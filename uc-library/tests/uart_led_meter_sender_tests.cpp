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
    if (operation == 'v')
      sender.setLedMeterPosition(a, b, c);
    else if (operation == 'c')
      sender.setLedMeterPositionCA(a, b, c);
    else {
      assert(operation == 'n');
      sender.setLedMeterClip(a, b);
    }
    assert(capture.calls == 1 && capture.writes == 1);
    const auto expectedWire =
        operation == 'n' ? hex(static_cast<unsigned>(b) & 255, 2) + "71N"
                         : hex(static_cast<unsigned>(b) & 255, 2) +
                               hex(static_cast<unsigned>(c) & 255, 2) +
                               (operation == 'c' ? "2V" : "0V");
    assert(capture.wire == expectedWire);
    assert(capture.wire.size() == (operation == 'n' ? 5U : 6U));
    assert(capture.result == (capture.mode == 0 ? 1 : 0));
    std::string raw;
    for (auto byte : capture.raw)
      raw += hex(byte, 2);
    for (char &byte : raw)
      byte = static_cast<char>(std::tolower(static_cast<unsigned char>(byte)));
    assert(raw == originalRaw); // All FOUR original bytes initialized.
    (void)seed;
    (void)originalReturn; // No original return declaration inference.
    ++count;
  }
  assert(in.eof() && count == 12288);
  std::cout << "PASS cases=" << count << " real_provider_calls=" << count
            << " all_four_bytes=true lengths=6,5 all_write_results=true\n";
}
