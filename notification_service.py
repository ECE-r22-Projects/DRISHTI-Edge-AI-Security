import os
import requests


# ============================================================
# DRISHTI - TELEGRAM NOTIFICATION SERVICE
# Supports:
#   1. Text notifications
#   2. Photo + caption notifications
# ============================================================


# ============================================================
# TELEGRAM CONFIGURATION
# ============================================================


TELEGRAM_BOT_TOKEN = "8849978017:AAHQLg20oTrbUuiUIUt6v864pGTLCCNTB_E"

TELEGRAM_CHAT_ID = "7442852328"

# ============================================================
# CHECK TELEGRAM CONFIGURATION
# ============================================================

def telegram_configured():

    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM] Bot token is missing")
        return False

    if not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Chat ID is missing")
        return False

    return True


# ============================================================
# SEND TEXT MESSAGE
# ============================================================

def send_telegram_message(message):

    if not telegram_configured():

        print(
            "[TELEGRAM] Configuration incomplete"
        )

        return False

    try:

        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_BOT_TOKEN}"
            f"/sendMessage"
        )

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        if response.ok:

            print(
                "[TELEGRAM] Text message sent successfully"
            )

            return True

        print(
            "[TELEGRAM ERROR]",
            response.status_code,
            response.text
        )

        return False

    except requests.exceptions.Timeout:

        print(
            "[TELEGRAM ERROR] Request timed out"
        )

        return False

    except requests.exceptions.RequestException as e:

        print(
            "[TELEGRAM ERROR]",
            e
        )

        return False

    except Exception as e:

        print(
            "[TELEGRAM ERROR]",
            e
        )

        return False


# ============================================================
# SEND PHOTO + CAPTION
# ============================================================

def send_telegram_photo(
    image_path,
    caption=""
):

    if not telegram_configured():

        print(
            "[TELEGRAM] Configuration incomplete"
        )

        return False

    # --------------------------------------------------------
    # CHECK IMAGE
    # --------------------------------------------------------

    if not image_path:

        print(
            "[TELEGRAM] Image path is empty"
        )

        return False

    if not os.path.isfile(image_path):

        print(
            "[TELEGRAM] Image file not found:",
            image_path
        )

        return False

    # --------------------------------------------------------
    # TELEGRAM SEND PHOTO API
    # --------------------------------------------------------

    try:

        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_BOT_TOKEN}"
            f"/sendPhoto"
        )

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption
        }

        with open(
            image_path,
            "rb"
        ) as photo:

            files = {
                "photo": (
                    os.path.basename(image_path),
                    photo,
                    "image/jpeg"
                )
            }

            response = requests.post(
                url,
                data=payload,
                files=files,
                timeout=30
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if response.ok:

            print(
                "[TELEGRAM] Photo notification sent successfully"
            )

            return True

        # ----------------------------------------------------
        # TELEGRAM API ERROR
        # ----------------------------------------------------

        print(
            "[TELEGRAM PHOTO ERROR]",
            response.status_code
        )

        print(
            response.text
        )

        return False

    except requests.exceptions.Timeout:

        print(
            "[TELEGRAM PHOTO ERROR] Request timed out"
        )

        return False

    except requests.exceptions.RequestException as e:

        print(
            "[TELEGRAM PHOTO ERROR]",
            e
        )

        return False

    except Exception as e:

        print(
            "[TELEGRAM PHOTO ERROR]",
            e
        )

        return False


# ============================================================
# TEST TELEGRAM CONNECTION
# ============================================================

def test_telegram():

    message = (
        "🚨 DRISHTI TEST ALERT 🚨\n\n"
        "Telegram notification system is connected successfully."
    )

    return send_telegram_message(
        message
    )


# ============================================================
# TEST TELEGRAM PHOTO
# ============================================================

def test_telegram_photo(
    image_path
):

    caption = (
        "🚨 DRISHTI PHOTO TEST 🚨\n\n"
        "📸 Image notification system is working."
    )

    return send_telegram_photo(
        image_path,
        caption
    )


# ============================================================
# MODULE TEST
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )
    print(
        "     DRISHTI TELEGRAM SERVICE TEST"
    )
    print(
        "=========================================="
    )
    print()

    if telegram_configured():

        print(
            "[TELEGRAM] Configuration detected"
        )

        print(
            "[TELEGRAM] Chat ID:",
            TELEGRAM_CHAT_ID
        )

        print()

        test_telegram()

    else:

        print(
            "[TELEGRAM] Configuration NOT detected"
        )

        print()
        print(
            "Set these environment variables:"
        )

        print(
            "TELEGRAM_BOT_TOKEN"
        )

        print(
            "TELEGRAM_CHAT_ID"
        )

    print()