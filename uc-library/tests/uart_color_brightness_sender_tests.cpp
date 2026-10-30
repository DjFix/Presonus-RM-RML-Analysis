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
#include <vector>

std::string hex(unsigned value, int digits) {
  std::string out(static_cast<std::size_t>(digits), '0');
  for (int i = digits - 1; i >= 0; --i) {
    out[static_cast<std::size_t>(i)] = "0123456789ABCDEF"[value & 15];
    value >>= 4;
  }
  return out;
}
class Capture final : public Presonus::Panel::ProtocolComm {
public:
  int writeMsg(Uart_Msg_Type &value) override {
    raw.push_back(value.bytes);
    const auto before = wire.size();
    const int result = ProtocolComm::writeMsg(value);
    results.push_back(result);
    writerCalls.push_back(wire.size() - before);
    return result;
  }
  int open(const char *) override { throw std::logic_error("unexpected open"); }
  void close() override { throw std::logic_error("unexpected close"); }
  int enableHISpeed(bool) override {
    throw std::logic_error("unexpected speed");
  }
  int read(char *, int) override { throw std::logic_error("unexpected read"); }
  int write(const char *bytes, int count) override {
    wire.emplace_back(bytes, static_cast<std::size_t>(count));
    return mode == 0 ? count : mode == 1 ? count - 1 : mode == 2 ? 0 : -1;
  }
  std::vector<std::array<std::uint8_t, 4>> raw;
  std::vector<std::string> wire;
  std::vector<int> results;
  std::vector<std::size_t> writerCalls;
  int mode = 0;
};
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream in(argv[1]);
  assert(in);
  Capture capture;
  Presonus::UARTMessageSender sender(capture);
  char operation;
  int index, group, color, on, seed, originalReturn;
  unsigned rawCount, cases = 0, rejects = 0, frames = 0, special = 0;
  while (in >> operation >> index >> group >> color >> on >> seed >>
         originalReturn >> rawCount) {
    assert(on == 0 || on == 1);
    capture.raw.clear();
    capture.wire.clear();
    capture.results.clear();
    capture.writerCalls.clear();
    capture.mode = static_cast<int>((cases / 2) % 4);
    if (operation == 'b') {
      assert(index >= 0 && index <= 255);
      sender.setLedBrightness(static_cast<unsigned char>(index));
    } else if (operation == 'l')
      sender.setLedColorLinear(index, group, color, on != 0);
    else {
      assert(operation == 'r');
      sender.setLedColor(index, group, static_cast<RGBLedColors>(color),
                         on != 0);
      if (color == 16)
        ++special;
    }
    assert(capture.raw.size() == rawCount);
    std::size_t wireIndex = 0;
    for (std::size_t i = 0; i < rawCount; ++i) {
      std::string original;
      in >> original;
      assert(in && original.size() == 8);
      const auto &raw = capture.raw[i];
      std::string actual;
      for (auto byte : raw)
        actual += hex(byte, 2);
      for (char &byte : actual)
        byte =
            static_cast<char>(std::tolower(static_cast<unsigned char>(byte)));
      if (operation == 'b') {
        assert(actual.substr(0, 4) == original.substr(0, 4));
        assert(raw[2] == 0 && raw[3] == 0);
        auto tail = hex(static_cast<unsigned>(seed), 2);
        for (char &byte : tail)
          byte =
              static_cast<char>(std::tolower(static_cast<unsigned char>(byte)));
        assert(original.substr(4) == tail + tail);
      } else
        assert(actual == original); // All four bytes initialized in originals.
      Uart_Msg_Type msg{raw};
      char buffer[16]{};
      const int codec = uart_protocol_encode(&msg, buffer);
      if (raw[0] == 0x90 || (raw[0] >= 0xa0 && raw[0] <= 0xa2)) {
        assert(codec == -2 && capture.writerCalls[i] == 0 &&
               capture.results[i] == 0);
        ++rejects;
      } else {
        const auto expected =
            raw[0] == 0x4c
                ? hex(raw[1], 1) + hex(raw[2], 2) + hex(raw[3], 1) + "L"
                : hex(raw[1], 2) + hex(raw[2], 2) + hex(raw[3], 2) + "r";
        assert(raw[0] == 0x4c || raw[0] == 0x72);
        assert(codec == (raw[0] == 0x4c ? 5 : 7));
        assert(capture.writerCalls[i] == 1 &&
               capture.results[i] == (capture.mode == 0 ? 1 : 0));
        assert(capture.wire[wireIndex++] == expected &&
               std::string(buffer, codec) == expected);
        ++frames;
      }
    }
    assert(wireIndex == capture.wire.size());
    (void)originalReturn;
    ++cases;
  }
  assert(in.eof() && cases == 12288 && rejects == 16384 && frames > 0 &&
         special > 0);
  std::cout << "PASS cases=" << cases << " real_codec_rejections=" << rejects
            << " real_L_r_frames=" << frames << " special_color16=" << special
            << " full_order_bytes=true brightness_prefix2=true\n";
}
