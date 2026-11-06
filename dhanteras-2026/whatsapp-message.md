# Happy Dhanteras — WhatsApp Broadcast (Metal Craft Studio)

**Images**
- `dhanteras_post_1080x1350.png`: send with the broadcast message (4:5 portrait, shows in full in WhatsApp chats)
- `dhanteras_status_1080x1920.png`: for WhatsApp Status / Instagram Story (9:16)

Copy a message below and paste it as the **caption** of the image.
WhatsApp formatting: `*bold*`, `_italic_`.

---

## Option 1: Greeting (recommended)

```
✨🪔 *शुभ धनतेरस | Happy Dhanteras* 🪔✨

On this auspicious day, may Goddess Lakshmi and Lord Dhanvantari bless you and your family with *wealth, health & prosperity* 🙏

Dhanteras is the day we bring home new metal, a symbol of lasting fortune. May your home shine as bright as polished brass! 🏺💛

Thank you for being part of our journey.

Warm wishes,
*Team Metal Craft Studio* 
```

## Option 2: Greeting + soft invitation

```
🪔 *शुभ धनतेरस!* 🪔

Dhanteras is the most auspicious day to bring home something made of metal, and something that lasts. ✨

May this festival fill your home with *prosperity, good health and happiness.* 🙏

🏺 Planning a Dhanteras or Diwali purchase? Reply to this message or call us at [phone number] and our team will help you pick the perfect piece.

With gratitude,
*Metal Craft Studio*
[website / Instagram handle]
```

## Option 3: Short (Hindi + English)

```
🪔 *आपको और आपके परिवार को धनतेरस की हार्दिक शुभकामनाएँ!* 🪔

May Maa Lakshmi bless your home with wealth, health & happiness. ✨

— *Metal Craft Studio* 🙏
```

---

### Sending tips
- WhatsApp broadcasts only reach contacts who have **saved your number**.
- Send the image first with the message as its caption, so both arrive as one bubble.
- Replace the `[placeholders]` in Option 2 before sending.
- To change the poster text, edit `poster.html` and re-render with `node render.cjs` (needs Playwright).

### Using your real logo
The poster currently shows an **MCS monogram** placeholder. To use the official logo:
1. Save it as `dhanteras-2026/logo.png` (transparent PNG, light/gold version reads best on maroon).
2. Run `node render.cjs`. The logo replaces the monogram and the name line automatically.

### Products on the poster
The product shelf shows illustrated metal pieces: lantern, urli bowl, brass samai lamp, sun wall art, engraved vase.
Swap or edit them in the `<!-- product shelf -->` section of `poster.html` to match the actual catalogue.
