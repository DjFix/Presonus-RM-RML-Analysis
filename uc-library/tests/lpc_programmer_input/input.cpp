#include "capture_boundaries.hpp"
int main() {
  unsigned kind, expectedBits, fill, resultBits, expectedReads, expectedClocks;
  std::uint64_t start;
  int timeout;
  std::string script, expectedHex;
  unsigned count = 0;
  while (std::cin >> kind >> timeout >> expectedBits >> start >> fill >>
         script >> resultBits >> expectedHex >> expectedReads >>
         expectedClocks) {
    events.clear();
    reads = clocks = 0;
    nowMs = start;
    if (script != "-") {
      std::stringstream parser(script);
      std::string item;
      while (std::getline(parser, item, ',')) {
        for (char &c : item)
          if (c == ':')
            c = ' ';
        std::stringstream words(item);
        Event event;
        words >> event.result >> event.byte >> event.advance;
        assert(words && event.byte <= 255);
        events.push_back(event);
      }
    }
    presonus::lpc::InputState state;
    state.descriptor = 73;
    state.response.fill(static_cast<char>(fill));
    Presonus::LPCProgrammer programmer(presonus::lpc::InputOnly{}, state);
    int expected;
    static_assert(sizeof expected == sizeof expectedBits);
    std::memcpy(&expected, &expectedBits, sizeof expected);
    errno = 0;
    const int result = kind == 0   ? programmer.getNextChar(timeout)
                       : kind == 1 ? programmer.waitResponse(timeout)
                                   : programmer.waitResult(expected, timeout);
    assert(static_cast<unsigned>(result) == resultBits);
    assert(reads == expectedReads && clocks == expectedClocks);
    const auto &actual = presonus::lpc::InputAccess::state(programmer);
    assert(actual.descriptor == 73 && expectedHex.size() == 258);
    for (unsigned i = 0; i < 129; ++i)
      assert(
          static_cast<unsigned char>(actual.response[i]) ==
          ((nibble(expectedHex[2 * i]) << 4) | nibble(expectedHex[2 * i + 1])));
    ++count;
  }
  assert(count == 13640);
  std::cout << "PASS original_input_cases=" << count << '\n';
}
