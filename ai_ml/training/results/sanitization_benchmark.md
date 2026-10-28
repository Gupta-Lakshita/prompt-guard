# Sanitization Success Rate Benchmark

Synopsis Section 7 target: >=95%.

- Total labelled cases: 300
- Fully redacted (no known PII value leaked): 278
- **Sanitization Success Rate: 92.7%**

Methodology: each case embeds Faker-generated PII values (email, phone, name, Luhn-valid credit card, SSN, API key) into a template prompt via a fixed seed, so the exact ground-truth values are known. Each is run through the real `detect_pii()` -> `sanitize_prompt()` pipeline; a case is a 'success' only if none of its known values still appear verbatim in the sanitized output. This covers detection misses and redaction bugs together, matching the synopsis's end-result framing of this metric.

## Failures (22)

**Root cause, not just a tally:** 20/22 failures are phone numbers in formats `detect_pii()` doesn't match — mainly Faker-generated numbers with extensions (e.g. `311.279.8843x81667`) or international prefixes with extra grouping. This is a real PII-detection coverage gap (Presidio's phone recognizer and the regex fallback both miss these), not a sanitizer bug — whatever `detect_pii()` doesn't find, `sanitize_prompt()` can't redact. Narrowing this would mean widening `ai_ml/pii_detector.py`'s phone matching to cover extensions/international formats, at the cost of some risk of new false positives — a real tradeoff, left open rather than quietly patched to make this number look better.

| Original | Leaked value(s) | Sanitized output |
| --- | --- | --- |
| Call me at 311.279.8843x81667 tomorrow morning. | 311.279.8843x81667 | Call me at 311.279.8843x81667 tomorrow morning. |
| Here is my information: name Ashley Kim, email alvaradozachary@example.org, phone +1-744-574-2865x2321. | +1-744-574-2865x2321 | Here is my information: name [PERSON_REDACTED], email [EMAIL_REDACTED], phone +1-744-574-2865x2321. |
| Call me at +1-998-808-1722 tomorrow morning. | +1-998-808-1722 | Call me at +1-998-808-1722 tomorrow morning. |
| Call me at +1-282-321-6939x372 tomorrow morning. | +1-282-321-6939x372 | Call me at +1-282-321-6939x372 tomorrow morning. |
| Please register me with phone number 001-598-896-8095x06170. | 001-598-896-8095x06170 | Please register me with phone number 001-598-896-8095x06170. |
| Call me at 546.490.3904 tomorrow morning. | 546.490.3904 | Call me at 546.490.3904 tomorrow morning. |
| Call me at (294)817-3849x32246 tomorrow morning. | (294)817-3849x32246 | Call me at (294)817-3849x32246 tomorrow morning. |
| Here is my information: name Melissa Charles, email ashleybautista@example.net, phone 001-536-729-0897x249. | 001-536-729-0897x249 | Here is my information: name [PERSON_REDACTED], email [EMAIL_REDACTED], phone 001-536-729-0897x249. |
| Here is my information: name Elizabeth Taylor, email qkim@example.org, phone 2383877582. | 2383877582 | Here is my information: name [PERSON_REDACTED], email [EMAIL_REDACTED], phone 2383877582. |
| Call me at 001-896-851-5341x6257 tomorrow morning. | 001-896-851-5341x6257 | Call me at 001-896-851-5341x6257 tomorrow morning. |
| Call me at +1-625-973-0132x5135 tomorrow morning. | +1-625-973-0132x5135 | Call me at +1-625-973-0132x5135 tomorrow morning. |
| My name is Cameron Morris, please add me to the guest list. | Cameron Morris | My name is Cameron Morris, please add me to the guest list. |
| Call me at 001-827-321-2264 tomorrow morning. | 001-827-321-2264 | Call me at 001-827-321-2264 tomorrow morning. |
| Call me at +1-598-947-2706x31212 tomorrow morning. | +1-598-947-2706x31212 | Call me at +1-598-947-2706x31212 tomorrow morning. |
| Please register me with phone number 556.692.2076x19042. | 556.692.2076x19042 | Please register me with phone number 556.692.2076x19042. |
| Please register me with phone number 338.244.9647x7163. | 338.244.9647x7163 | Please register me with phone number 338.244.9647x7163. |
| Here is my information: name Alice Henry, email sean58@example.com, phone 001-485-530-8004x26654. | 001-485-530-8004x26654 | Here is my information: name [PERSON_REDACTED], email [EMAIL_REDACTED], phone 001-485-530-8004x26654. |
| Please register me with phone number 001-664-838-7280x93951. | 001-664-838-7280x93951 | Please register me with phone number 001-664-838-7280x93951. |
| Call me at 001-944-632-8876x2565 tomorrow morning. | 001-944-632-8876x2565 | Call me at 001-944-632-8876x2565 tomorrow morning. |
| Call me at +1-969-528-7382x71740 tomorrow morning. | +1-969-528-7382x71740 | Call me at +1-969-528-7382x71740 tomorrow morning. |
| Please register me with phone number +1-398-802-2739. | +1-398-802-2739 | Please register me with phone number +1-398-802-2739. |
| Here is my information: name Crystal Turner, email trevornoble@example.net, phone 502.657.9653. | Crystal Turner | Here is my information: name Crystal Turner, email [EMAIL_REDACTED], phone [PHONE_REDACTED]. |