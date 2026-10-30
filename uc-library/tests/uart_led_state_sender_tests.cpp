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
  int group, index;
  std::uint32_t rawState, callbackReturn;
  unsigned seed, count = 0;
  std::string original;
  while (in >> group >> index >> rawState >> callbackReturn >> seed >>
         original) {
    capture.mode = static_cast<int>(count % 4);
    capture.calls = capture.writes = 0;
    sender.setLedState(group, index, static_cast<kLedStates>(rawState));
    assert(capture.calls == 1 && capture.writes == 1);
    std::string raw;
    for (auto byte : capture.raw)
      raw += hex(byte, 2);
    for (char &byte : raw)
      byte = static_cast<char>(std::tolower(static_cast<unsigned char>(byte)));
    assert(raw == original); // Exact FOUR-byte original helper payload.
    const auto expected = hex(static_cast<unsigned>(group) & 255, 1) +
                          hex(static_cast<unsigned>(index) & 255, 2) +
                          hex(rawState & 255, 1) + "L";
    assert(capture.wire == expected && capture.wire.size() == 5);
    assert(capture.result == (capture.mode == 0 ? 1 : 0));
    // Token kind/underlying and valid ORIGINAL C++ enum values are NOT proved.
    (void)callbackReturn;
    (void)seed;
    ++count;
  }
  assert(in.eof() && count == 8192);
  std::cout
      << "PASS cases=" << count
      << " real_L_frames=8192 all_four_bytes=true type_fidelity_pending=true\n";
}
