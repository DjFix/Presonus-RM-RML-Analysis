#include "presonus/panel/uart_message.hpp"
#include "presonus/panel/uart_message_sender.hpp"
#include <array>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

class Capture final : public Presonus::Panel::ProtocolComm {
public:
  int writeMsg(Uart_Msg_Type &value) override {
    ++calls;
    raw = value.bytes;
    result = ProtocolComm::writeMsg(value); // Real lock/codec/virtual writer.
    return result;
  }
  int open(const char *) override { throw std::logic_error("unexpected open"); }
  void close() override { throw std::logic_error("unexpected close"); }
  int enableHISpeed(bool) override {
    throw std::logic_error("unexpected speed");
  }
  int read(char *, int) override { throw std::logic_error("unexpected read"); }
  int write(const char *bytes, int count) override {
    ++writes;
    wire.assign(bytes, static_cast<std::size_t>(count));
    return mode == 0 ? count : mode == 1 ? count - 1 : mode == 2 ? 0 : -1;
  }
  std::array<std::uint8_t, 4> raw{};
  std::string wire;
  int mode = 0, calls = 0, writes = 0, result = 0;
};
std::string hex(unsigned value, int digits) {
  std::string out(static_cast<std::size_t>(digits), '0');
  for (int i = digits - 1; i >= 0; --i) {
    out[static_cast<std::size_t>(i)] = "0123456789ABCDEF"[value & 15];
    value >>= 4;
  }
  return out;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream in(argv[1]);
  assert(in);
  Capture capture;
  Presonus::UARTMessageSender sender(capture);
  char operation;
  int a, b, c, seed, originalReturn;
  std::string originalRaw;
  unsigned count = 0;
  while (in >> operation >> a >> b >> c >> seed >> originalReturn >>
         originalRaw) {
    capture.mode = static_cast<int>(count % 4);
    capture.calls = capture.writes = 0;
    if (operation == 'f')
      sender.setFaderPosition(a, b);
    else {
      assert(operation == 'd');
      sender.setDigitalPot(a, b, c);
    }
    assert(capture.calls == 1 && capture.writes == 1);
    const auto expectedWire =
        operation == 'f' ? hex(static_cast<unsigned>(a) & 255, 2) +
                               hex(static_cast<unsigned>(b) & 65535, 3) + "f"
                         : hex(static_cast<unsigned>(b) & 255, 2) +
                               hex(static_cast<unsigned>(c) & 255, 2) + "d";
    assert(capture.wire == expectedWire);
    assert(capture.wire.size() == (operation == 'f' ? 6U : 5U));
    assert(capture.result == (capture.mode == 0 ? 1 : 0));
    std::string raw;
    for (auto byte : capture.raw)
      raw += hex(byte, 2);
    // ARM evidence initializes4 bytes for fader, only3 for pot. Do not compare
    // or read any native uninitialized storage to emulate the original tail.
    const std::size_t initialized = operation == 'f' ? 8 : 6;
    for (std::size_t i = 0; i < initialized; ++i)
      assert(std::tolower(static_cast<unsigned char>(raw[i])) ==
             originalRaw[i]);
    if (operation == 'd') {
      assert(capture.raw[3] == 0); // Explicit deterministic source-port choice.
      auto seededTail = hex(static_cast<unsigned>(seed), 2);
      for (char &byte : seededTail)
        byte =
            static_cast<char>(std::tolower(static_cast<unsigned char>(byte)));
      assert(originalRaw.substr(6) == seededTail);
    }
    (void)originalReturn; // The original return declaration is unresolved.
    ++count;
  }
  assert(in.eof() && count == 8192);
  std::cout
      << "PASS cases=" << count << " real_provider_calls=" << count
      << " initialized_prefix_only=true lengths=6,5 all_write_results=true\n";
}
