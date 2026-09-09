# Contributing to FocusGuard

Thank you for your interest in contributing to FocusGuard! We welcome issues, bug reports, and pull requests to help keep FocusGuard robust, lightweight, and effective for private home networks.

---

## Development Guidelines

1. **Keep it Lightweight**: FocusGuard is built specifically for minimal Linux environments (DietPi on single-board computers like Raspberry Pi). Avoid introducing heavy dependencies or compilation requirements.
2. **Technical Honesty**: Clearly communicate network limitations (e.g. DoH, VPNs, IPv6) rather than making misleading promises.
3. **Privacy by Design**: Never inspect or decrypt HTTPS packet payloads.
4. **Test Everything**: Any change to domain normalization, the DNS engine, state persistence, or the locked state machine must be accompanied by unit tests in `tests/`.

---

## Local Setup & Testing

1. Clone your fork:
   ```bash
   git clone https://github.com/za-m-an/Focus-Guard.git
   cd Focus-Guard
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # or .venv\Scripts\activate on Windows
   ```

3. Install testing tools:
   ```bash
   pip install pytest pytest-asyncio anyio
   ```

4. Run the test suite:
   ```bash
   python -m pytest tests -v
   ```

---

## Submitting a Pull Request

1. Create a descriptive feature branch (`git checkout -b feature/awesome-feature`).
2. Commit your changes with clear, concise commit messages.
3. Verify that all automated tests pass (`python -m pytest tests`).
4. Push to your branch and open a Pull Request against `main`.
