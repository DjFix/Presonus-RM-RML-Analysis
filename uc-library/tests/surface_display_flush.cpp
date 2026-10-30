#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/BitmapDrawing.hpp"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using Access = presonus::surface_panel_port::BitmapDrawingAccess;
static std::vector<unsigned char> decode(const std::string &s) {
  std::vector<unsigned char> b;
  for (unsigned i = 0; i < s.size(); i += 2)
    b.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return b;
}
class CaptureIO final : public Presonus::Panel::IPanelIO {
public:
  std::string packets;
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &m) override {
    const char *h = "0123456789abcdef";
    for (unsigned char byte : m.bytes) {
      packets += h[byte >> 4];
      packets += h[byte & 15];
    }
    packets += ':';
    char encoded[128]{};
    if (uart_protocol_encode(&m, encoded) <= 0)
      throw std::runtime_error("genuine UART codec rejected message");
    return -17;
  }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  int port, force, dirty, expectedDirty;
  std::string current, cache, expectedCurrent, expectedCache, expectedPackets;
  unsigned cases = 0;
  while (in >> port >> force >> dirty >> expectedDirty >> current >> cache >>
         expectedCurrent >> expectedCache >> expectedPackets) {
    Presonus::Panel::BitmapDisplay display;
    CaptureIO io;
    auto c = decode(current), old = decode(cache);
    auto &bits = Access::bitmap(display);
    auto &previous = Access::lastSent(display);
    std::copy(c.begin(), c.end(), bits.begin());
    std::copy(old.begin(), old.end(), previous.begin());
    Access::dirty(display, dirty);
    display.setPort(port ? &io : nullptr);
    if (Access::port(display) != (port ? &io : nullptr))
      throw std::runtime_error("port identity");
    display.update(force);
    auto ec = decode(expectedCurrent), eo = decode(expectedCache);
    if (!std::equal(ec.begin(), ec.end(), bits.begin()) ||
        !std::equal(eo.begin(), eo.end(), previous.begin()) ||
        Access::textDirty(display) != bool(expectedDirty) ||
        io.packets != (expectedPackets == "-" ? "" : expectedPackets))
      throw std::runtime_error("flush packets/cache/dirty differ case" +
                               std::to_string(cases));
    ++cases;
  }
  std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
}
