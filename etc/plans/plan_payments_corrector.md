# Plan: Fix Payment Error Message in Telegram Bot

## Problem Description
When users navigate to **Profile → Balance → Buy Batteries** and click a button to purchase batteries for Telegram Stars, the bot first displays an error message "❌ Something went wrong. Please try again." and then sends the correct invoice. The payment itself works successfully, but the error message is confusing and unnecessary.

## Root Cause Analysis

### Location
File: `telegram_bot/handlers.py`
Function: `callback_query_handler` (lines 405-1094)

### The Issue
The `elif data.startswith("buy_battery:"):` block (lines 462-540) handles battery purchase requests. After successfully sending the invoice via `query.message.reply_invoice()`, the code does NOT return early. This causes execution to continue to lines 1063-1074 where the function tries to edit the callback query message:

```python
try:
    await query.edit_message_text(
        text=message,  # 'message' is NOT defined for buy_battery case!
        reply_markup=keyboard,  # 'keyboard' is NOT defined for buy_battery case!
        parse_mode="HTML"
    )
```

Since `message` and `keyboard` variables are only defined for specific callback data cases (like "balance", "profile", etc.) but NOT for the `buy_battery:` case, Python raises an `UnboundLocalError`:
```
cannot access local variable 'message' where it is not associated with a value
```

This error is caught by the outer exception handler (lines 1076-1094), which sends the generic error message to the user.

### Terminal Output Evidence
```
INFO:telegram_bot.handlers:Invoice sent successfully for payment payment_16_a1e30b5af6c6f5ea
ERROR:telegram_bot.handlers:Error in callback query handler: cannot access local variable 'message' where it is not associated with a value
```

## Solution

Add a `return` statement after successfully sending the invoice to prevent the code from falling through to the message editing section.

### Code Changes Required

**File:** `telegram_bot/handlers.py`

**Location:** After line 530 (inside the `elif data.startswith("buy_battery:"):` block)

**Current Code (lines 511-540):**
```python
            # Отправляем invoice через Telegram Stars API
            try:
                # Создаём invoice для Telegram Stars
                invoice_title = f"{batteries_count} Batteries" if user_lang == 'en' else f"{batteries_count} Батареек"
                invoice_description = f"Buy {batteries_count} batteries for tAIger bot" if user_lang == 'en' else f"Купить {batteries_count} батареек для бота tAIger"

                # Отправляем invoice БЕЗ reply_markup (Telegram сам добавит кнопку Pay)
                await query.message.reply_invoice(
                    title=invoice_title,
                    description=invoice_description,
                    payload=pre_checkout_id,  # Используем как payload
                    provider_token="",  # Пустой для Telegram Stars
                    currency="XTR",  # XTR - код валюты Telegram Stars
                    prices=[{"label": f"{batteries_count} batteries" if user_lang == 'en' else f"{batteries_count} батареек", "amount": batteries_count}],
                    max_tip_amount=0,
                    start_parameter="buy-batteries"
                    # reply_markup НЕ используется - Telegram сам добавит кнопку Pay
                )

                logger.info(f"Invoice sent successfully for payment {pre_checkout_id}")

            except Exception as e:
                logger.error(f"Error creating invoice: {e}")
                await query.answer(f"❌ Error: {str(e)}")
                # Отправляем сообщение об ошибке
                await query.message.reply_text(
                    "❌ Something went wrong. Please try again.",
                    reply_markup=BotKeyboards.back_to_main(user_lang)
                )
```

**Fixed Code (add `return` after line 530):**
```python
            # Отправляем invoice через Telegram Stars API
            try:
                # Создаём invoice для Telegram Stars
                invoice_title = f"{batteries_count} Batteries" if user_lang == 'en' else f"{batteries_count} Батареек"
                invoice_description = f"Buy {batteries_count} batteries for tAIger bot" if user_lang == 'en' else f"Купить {batteries_count} батареек для бота tAIger"

                # Отправляем invoice БЕЗ reply_markup (Telegram сам добавит кнопку Pay)
                await query.message.reply_invoice(
                    title=invoice_title,
                    description=invoice_description,
                    payload=pre_checkout_id,  # Используем как payload
                    provider_token="",  # Пустой для Telegram Stars
                    currency="XTR",  # XTR - код валюты Telegram Stars
                    prices=[{"label": f"{batteries_count} batteries" if user_lang == 'en' else f"{batteries_count} батареек", "amount": batteries_count}],
                    max_tip_amount=0,
                    start_parameter="buy-batteries"
                    # reply_markup НЕ используется - Telegram сам добавит кнопку Pay
                )

                logger.info(f"Invoice sent successfully for payment {pre_checkout_id}")
                return  # <-- ADD THIS LINE: Exit early after sending invoice

            except Exception as e:
                logger.error(f"Error creating invoice: {e}")
                await query.answer(f"❌ Error: {str(e)}")
                # Отправляем сообщение об ошибке
                await query.message.reply_text(
                    "❌ Something went wrong. Please try again.",
                    reply_markup=BotKeyboards.back_to_main(user_lang)
                )
                return  # <-- ALSO ADD THIS LINE: Exit early on error
```

## Implementation Steps

1. **Open file:** `telegram_bot/handlers.py`
2. **Navigate to line 530** (after `logger.info(f"Invoice sent successfully for payment {pre_checkout_id}")`)
3. **Add `return` statement** on a new line after line 530
4. **Add `return` statement** on a new line after line 539 (inside the exception handler)
5. **Save the file**

## Testing

After applying the fix, verify:

1. Navigate to **Profile → Balance → Buy Batteries**
2. Click any battery purchase button (e.g., "5 Batteries")
3. **Expected behavior:** The invoice should appear immediately WITHOUT any error message
4. Complete the payment to ensure the payment flow still works correctly
5. Check logs to confirm no errors appear

## Expected Result

- ✅ No error message "❌ Something went wrong. Please try again." appears
- ✅ Invoice is sent immediately when user clicks purchase button
- ✅ Payment flow works correctly
- ✅ No `UnboundLocalError` in logs
- ✅ Clean user experience

## Additional Notes

- The fix is minimal and surgical - only adding two `return` statements
- This follows the pattern used elsewhere in the function (e.g., line 446 for "main_menu", line 773 for "bot_settings", line 788, line 909)
- The `return` statement prevents the code from falling through to the generic message editing section that expects `message` and `keyboard` variables to be defined
