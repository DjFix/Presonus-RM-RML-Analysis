#include "presonus/noaa/spi_packets.hpp"
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::int64_t ticks[] = {-1000001, 2999999, -3999999, INT64_MAX, INT64_MIN,
                        0,        1000000, -999999,  999999};
unsigned calls;
unsigned mask;
bool releaseCallback;
std::ostringstream events;
presonus::noaa::SpiPacketState *state;
Presonus::NOAA::TCardSPI *transport;
std::string hex(const unsigned char *data, unsigned count) {
  const char *digits = "0123456789abcdef";
  std::string out;
  for (unsigned i = 0; i < count; ++i) {
    out += digits[data[i] >> 4];
    out += digits[data[i] & 15];
  }
  return out;
}
std::string packetSummary(const Presonus::NOAA::SysexPacket &packet) {
  std::ostringstream out;
  const auto &m = packet.portableMetadata();
  out << unsigned(packet.length) << ',' << m.headerWords[0] << ','
      << m.headerWords[1] << ',' << m.constructedQuotient;
  for (auto word : m.trailingWords)
    out << ',' << word;
  out << ',' << hex(packet.bytes.data(), 255);
  return out.str();
}
class Receiver : public Presonus::NOAA::ISysexReceiver {
public:
  unsigned id = 0;
  bool accepts(const Presonus::NOAA::SysexPacket &packet) override {
    events << 'A' << id << ':' << packetSummary(packet) << ';';
    return mask & (1u << id);
  }
  void receive(const Presonus::NOAA::SysexPacket &packet) override {
    events << 'R' << id << ':' << packetSummary(packet) << ';';
    if (releaseCallback)
      transport->release();
  }
};
} // namespace

namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  if (calls % 3 == 2 && state->count != 0)
    throw std::runtime_error("count must reset before third clock");
  return ticks[calls++ % 9];
}
} // namespace presonus::dice

extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *format, ...) {
  if (std::string(format) != "Warning no Receiver found for packet")
    throw std::runtime_error(
        "Unexpected source-port error in equivalence corpus");
  events << "W;";
}
extern "C" void __wrap__ZNK8Presonus4NOAA11SysexPacket3logEv(
    const Presonus::NOAA::SysexPacket *packet) {
  events << 'P' << ':' << packetSummary(*packet) << ';';
}

int main() {
  unsigned total;
  if (!(std::cin >> total))
    return 2;
  for (unsigned index = 0; index < total; ++index) {
    std::string name, seedText;
    char mode;
    std::uint32_t count;
    unsigned disabled, receivers, releaseFlag, chunks;
    if (!(std::cin >> name >> mode >> seedText >> count >> disabled >>
          receivers >> mask >> releaseFlag >> chunks) ||
        seedText.size() != 512 || receivers > 4 || disabled > 255)
      return 3;
    std::array<unsigned char, 256> seed{};
    for (unsigned i = 0; i < 256; ++i)
      seed[i] = static_cast<unsigned char>(
          std::stoul(seedText.substr(2 * i, 2), nullptr, 16));
    presonus::noaa::SpiPacketState owned(seed, count, disabled, 4);
    Presonus::NOAA::TCardSPI spi(owned);
    Receiver receiver[4];
    for (unsigned i = 0; i < receivers; ++i) {
      receiver[i].id = i;
      spi.registerReceiver(receiver + i);
    }
    state = &owned;
    transport = &spi;
    calls = 0;
    events.str("");
    events.clear();
    releaseCallback = releaseFlag;
    if (mode == 'r')
      spi.release();
    else if (mode != 'a')
      return 4;
    for (unsigned i = 0; i < chunks; ++i) {
      int length;
      std::string text;
      if (!(std::cin >> length >> text))
        return 5;
      std::vector<unsigned char> bytes;
      if (text != "-") {
        for (unsigned j = 0; j < text.size(); j += 2)
          bytes.push_back(static_cast<unsigned char>(
              std::stoul(text.substr(j, 2), nullptr, 16)));
      }
      if (length > 0 && static_cast<unsigned>(length) > bytes.size())
        return 6;
      spi.assembleSYSEX(bytes.empty() ? nullptr : bytes.data(), length);
    }
    if (owned.error != presonus::noaa::SpiPacketError::none)
      return 7;
    std::cout << name << ' ' << owned.count << ' ' << unsigned(owned.disabled)
              << ' ' << calls << ' ' << hex(owned.span(), 256) << ' '
              << events.str() << '\n';
  }
}
