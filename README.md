# Empório da Música Service Agent

Text-message customer service agent prototype for Empório da Música, a fictional musical instrument
store.

## Assumptions

The store manual contradicts itself on the WhatsApp number, the email address and the credit card
installment minimums. The rules the agent follows, and the questions still open with the store, are
in [Stakeholder Clarifications](docs/stakeholder-clarifications.md). Issues in the store data are in
[Store Data Corner Cases](docs/corner-cases/store-data.md).

## Known Limitations

> **Draft:** this describes planned behavior for the chat, which is not built yet.

- **Crash details:** `make run` hides application crash details from the browser, and `make run-dev`
  shows them in full to make debugging easier. Streamlit displays these details itself, so they skip
  the step that removes secrets. A secret in a crash message could appear on screen in `make run-dev`,
  so review any screenshot of a crash before sharing it.
