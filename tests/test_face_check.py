"""Face check at pickup: recipient registration, cashier check, one-time code fallback."""
import io
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from app import FACE_MAX_FAILURES, app, connect, init_db, seed_db
from ml.face import service
from seed_kfc import seed_kfc

FACES = Path(__file__).resolve().parent / "data" / "faces"
CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


def photo(name):
    return (FACES / name).read_bytes()


@unittest.skipUnless(service.available(), "OpenCV or face models missing")
class FaceServiceTests(unittest.TestCase):
    def test_same_person_matches_and_different_person_does_not(self):
        a1 = service.embed(service.decode_image(photo("person-a-1.jpg")))
        a2 = service.decode_image(photo("person-a-2.jpg"))
        b1 = service.decode_image(photo("person-b-1.jpg"))
        same = service.compare(a1, a2)
        other = service.compare(a1, b1)
        self.assertTrue(same.matched, same)
        self.assertFalse(other.matched, other)
        self.assertGreater(same.score, other.score)

    def test_photo_without_a_face_is_refused_with_a_clear_message(self):
        import cv2
        blank = cv2.imencode(".jpg", np.full((480, 640, 3), 200, np.uint8))[1].tobytes()
        with self.assertRaisesRegex(service.FaceError, "No face"):
            service.embed(service.decode_image(blank))

    def test_unreadable_upload_is_refused(self):
        with self.assertRaises(service.FaceError):
            service.decode_image(b"not an image")

    def test_faceprint_round_trips_as_text_without_storing_the_photo(self):
        print_ = service.embed(service.decode_image(photo("person-a-1.jpg")))
        text = service.to_text(print_)
        self.assertEqual(len(service.from_text(text)), 128)
        self.assertAlmostEqual(service.similarity(print_, service.from_text(text)), 1.0, places=4)


@unittest.skipUnless(service.available(), "OpenCV or face models missing")
class FaceCheckFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "test.db")
        app.config.update(TESTING=True, DATABASE=self.database)
        init_db(self.database)
        seed_db(self.database)
        seed_kfc(self.database)
        self.sender = app.test_client()
        self.recipient = app.test_client()
        self.cashier = app.test_client()
        db = connect(self.database)
        self.item = db.execute(
            "SELECT mi.id, mi.merchant_id, m.name FROM menu_items mi JOIN merchants m ON m.id = mi.merchant_id "
            "WHERE m.name = 'KFC' AND mi.is_active = 1 ORDER BY mi.id LIMIT 1").fetchone()
        db.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    # -- helpers --------------------------------------------------------------
    def csrf(self, client, url):
        """The session's CSRF token (pages without a form fall back to the buy page)."""
        found = CSRF.search(client.get(url).get_data(as_text=True))
        if not found:
            found = CSRF.search(client.get(f"/buy/menu/{self.item['id']}").get_data(as_text=True))
        return found.group(1)

    def buy(self, face_lock=True):
        url = f"/buy/menu/{self.item['id']}"
        data = {"csrf_token": self.csrf(self.sender, url), "sender_name": "Amina",
                "recipient_phone": "0770123456", "message": "", "payment_method": "mtn"}
        if face_lock:
            data["face_lock"] = "1"
        response = self.sender.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        return urlparse(response.headers["Location"]).path.rsplit("/", 1)[-1]

    def register(self, client, code, name="person-a-1.jpg", consent=True):
        data = {"csrf_token": self.csrf(client, f"/voucher/{code}"),
                "photo": (open(FACES / name, "rb"), "face.jpg")}
        if consent:
            data["consent"] = "yes"
        return client.post(f"/voucher/{code}/face", data=data, content_type="multipart/form-data")

    def sign_in_cashier(self):
        with self.cashier.session_transaction() as session:
            session["cashier"] = {"merchant_id": self.item["merchant_id"], "name": self.item["name"]}

    A_SCAN = ["live-a-center.jpg", "live-a-left.jpg", "live-a-right.jpg", "live-a-center-2.jpg"]
    B_SCAN = ["live-b-center.jpg", "live-b-left.jpg", "live-b-right.jpg", "live-b-center.jpg"]

    def live_scan(self, client, purpose, code, frames, consent="yes"):
        """Run the live scan with a fixed step order (straight, left, right, straight)."""
        token = self.csrf(client, f"/merchant/verify?code={code}" if purpose == "cashier" else f"/voucher/{code}")
        started = client.post("/face/live/start", data={"csrf_token": token, "purpose": purpose,
                                                        "voucher_code": code, "consent": consent})
        if started.status_code != 200:
            return started
        with client.session_transaction() as session:
            state = session["face_live"]
            state["steps"] = ["center", "left", "right", "final"]
            session["face_live"] = state
        reply = None
        for name in frames:
            reply = client.post("/face/live/frame", content_type="multipart/form-data",
                                data={"csrf_token": token, "photo": (open(FACES / name, "rb"), "f.jpg")})
            if reply.get_json().get("done") or reply.get_json().get("restart"):
                break
        return reply

    def face_check(self, code, frames):
        return self.live_scan(self.cashier, "cashier", code, frames)

    def redeem(self, code):
        token = self.csrf(self.cashier, f"/merchant/verify?code={code}")
        return self.cashier.post("/merchant/redeem", data={"csrf_token": token, "voucher_code": code})

    def voucher(self, code):
        db = connect(self.database)
        row = db.execute("SELECT * FROM vouchers WHERE voucher_code = ?", (code,)).fetchone()
        db.close()
        return row

    def outcomes(self, code):
        db = connect(self.database)
        rows = db.execute("SELECT outcome, verify_method, face_score FROM audit_log WHERE voucher_code = ? "
                          "ORDER BY id", (code,)).fetchall()
        db.close()
        return rows

    # -- tests ----------------------------------------------------------------
    def test_face_lock_is_on_by_default_and_saved_with_the_voucher(self):
        page = self.sender.get(f"/buy/menu/{self.item['id']}").get_data(as_text=True)
        self.assertRegex(page, r'id="face_lock" name="face_lock" value="1"\s+checked')
        self.assertEqual(self.voucher(self.buy())["face_lock"], 1)
        self.assertEqual(self.voucher(self.buy(face_lock=False))["face_lock"], 0)

    def test_sender_cannot_register_their_own_face(self):
        code = self.buy()
        self.assertIn("Protected by a face check", self.sender.get(f"/voucher/{code}").get_data(as_text=True))
        response = self.register(self.sender, code)
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.voucher(code)["face_print"])

    def test_recipient_registers_once_with_consent_and_no_photo_is_stored(self):
        code = self.buy()
        self.assertIn("Register your face", self.recipient.get(f"/voucher/{code}").get_data(as_text=True))
        self.assertEqual(self.register(self.recipient, code, consent=False).status_code, 400)
        response = self.register(self.recipient, code)
        self.assertEqual(response.status_code, 200, response.get_json())
        stored = self.voucher(code)
        self.assertEqual(len(service.from_text(stored["face_print"])), 128)
        self.assertNotIn(b"JFIF", stored["face_print"].encode())
        self.assertIn("Face registered", self.recipient.get(f"/voucher/{code}").get_data(as_text=True))
        # A second registration (e.g. someone the link was forwarded to) is refused.
        self.assertEqual(self.register(app.test_client(), code, name="person-b-1.jpg").status_code, 409)

    def test_cashier_cannot_redeem_before_checking_the_recipient(self):
        code = self.buy()
        self.register(self.recipient, code)
        self.sign_in_cashier()
        page = self.cashier.get(f"/merchant/verify?code={code}").get_data(as_text=True)
        self.assertIn("Recipient check", page)
        self.redeem(code)
        self.assertEqual(self.voucher(code)["status"], "ACTIVE")

    def test_wrong_face_is_rejected_and_right_face_unlocks_redemption(self):
        code = self.buy()
        self.register(self.recipient, code, name="live-a-center.jpg")
        self.sign_in_cashier()
        wrong = self.face_check(code, self.B_SCAN).get_json()
        self.assertFalse(wrong["matched"])
        self.assertEqual(self.voucher(code)["face_failures"], 1)
        right = self.face_check(code, self.A_SCAN).get_json()
        self.assertTrue(right["matched"], right)
        self.redeem(code)
        used = self.voucher(code)
        self.assertEqual(used["status"], "USED")
        self.assertIsNone(used["face_print"], "faceprint must be deleted after pickup")
        log = [(r["outcome"], r["verify_method"]) for r in self.outcomes(code)]
        self.assertEqual(log, [("FACE_NO_MATCH", "face"), ("FACE_MATCH", "face"), ("REDEEMED", "face")])

    def test_repeated_mismatches_force_the_one_time_code(self):
        code = self.buy()
        self.register(self.recipient, code, name="live-a-center.jpg")
        self.sign_in_cashier()
        for _ in range(FACE_MAX_FAILURES):
            self.assertFalse(self.face_check(code, self.B_SCAN).get_json()["matched"])
        self.assertEqual(self.face_check(code, self.A_SCAN).status_code, 429)

    def test_recipient_can_register_with_the_live_scan(self):
        code = self.buy()
        reply = self.live_scan(self.recipient, "register", code, self.A_SCAN).get_json()
        self.assertTrue(reply["done"], reply)
        self.assertIsNotNone(self.voucher(code)["face_print"])
        # and the cashier's live scan of the same person then matches
        self.sign_in_cashier()
        self.assertTrue(self.face_check(code, self.A_SCAN).get_json()["matched"])

    def test_live_scan_needs_consent_and_blocks_the_sender(self):
        code = self.buy()
        self.assertEqual(self.live_scan(self.recipient, "register", code, self.A_SCAN, consent="").status_code, 400)
        self.assertEqual(self.live_scan(self.sender, "register", code, self.A_SCAN).status_code, 403)

    def test_a_still_photo_never_passes_the_head_turns(self):
        code = self.buy()
        self.register(self.recipient, code, name="live-a-center.jpg")
        self.sign_in_cashier()
        reply = self.face_check(code, ["live-a-center.jpg"] * 8).get_json()
        self.assertFalse(reply.get("done"), reply)
        self.assertEqual(reply["step"], 1)          # stuck at "turn your head"
        self.assertIn("turn your head", reply["prompt"].lower())
        self.assertIsNone(self.voucher(code)["pickup_verified_at"])

    def test_swapping_people_during_the_scan_restarts_it(self):
        code = self.buy()
        self.register(self.recipient, code, name="live-a-center.jpg")
        self.sign_in_cashier()
        reply = self.face_check(code, ["live-a-center.jpg", "live-b-left.jpg"]).get_json()
        self.assertTrue(reply["restart"], reply)
        self.assertIsNone(self.voucher(code)["pickup_verified_at"])

    def test_old_single_photo_cashier_check_is_gone(self):
        code = self.buy()
        self.sign_in_cashier()
        token = self.csrf(self.cashier, f"/merchant/verify?code={code}")
        response = self.cashier.post("/merchant/face-check", data={"csrf_token": token, "voucher_code": code})
        self.assertEqual(response.status_code, 404)

    def test_one_time_code_fallback_when_no_face_was_registered(self):
        code = self.buy()
        self.sign_in_cashier()
        page = self.cashier.get(f"/merchant/verify?code={code}").get_data(as_text=True)
        self.assertIn("has not registered a face", page)
        token = self.csrf(self.cashier, f"/merchant/verify?code={code}")
        sent = self.cashier.post("/merchant/pickup-code/send", data={"csrf_token": token, "voucher_code": code},
                                 follow_redirects=True).get_data(as_text=True)
        pickup_code = re.search(r"pickup code is (\d{6})", sent).group(1)
        wrong = "000000" if pickup_code != "000000" else "111111"
        token = self.csrf(self.cashier, f"/merchant/verify?code={code}")
        self.cashier.post("/merchant/pickup-code/check",
                          data={"csrf_token": token, "voucher_code": code, "pickup_code": wrong})
        self.assertEqual(self.voucher(code)["status"], "ACTIVE")
        token = self.csrf(self.cashier, f"/merchant/verify?code={code}")
        self.cashier.post("/merchant/pickup-code/check",
                          data={"csrf_token": token, "voucher_code": code, "pickup_code": pickup_code})
        self.redeem(code)
        self.assertEqual(self.voucher(code)["status"], "USED")
        outcomes = [r["outcome"] for r in self.outcomes(code)]
        self.assertEqual(outcomes, ["CODE_SENT", "CODE_WRONG", "CODE_OK", "REDEEMED"])

    def test_gifts_without_face_lock_redeem_as_before(self):
        code = self.buy(face_lock=False)
        self.sign_in_cashier()
        self.assertNotIn("Recipient check", self.cashier.get(f"/merchant/verify?code={code}").get_data(as_text=True))
        self.redeem(code)
        self.assertEqual(self.voucher(code)["status"], "USED")

    def test_large_uploads_are_allowed_only_on_face_endpoints(self):
        code = self.buy()
        big = b"x" * (2 * 1024 * 1024)
        token = self.csrf(self.recipient, f"/voucher/{code}")
        response = self.recipient.post(f"/voucher/{code}/face", content_type="multipart/form-data",
                                       data={"csrf_token": token, "consent": "yes", "photo": (io.BytesIO(big), "f.jpg")})
        self.assertIn(response.status_code, (400, 413))  # refused before any processing
        self.assertIsNone(self.voucher(code)["face_print"])
        token = self.csrf(self.recipient, f"/voucher/{code}")
        normal = self.recipient.post(f"/voucher/{code}/face", content_type="multipart/form-data",
                                     data={"csrf_token": token, "consent": "yes",
                                           "photo": (io.BytesIO(b"y" * (200 * 1024)), "f.jpg")})
        self.assertEqual(normal.status_code, 422, normal.get_data(as_text=True)[:300])  # accepted size, but not a face


if __name__ == "__main__":
    unittest.main()
