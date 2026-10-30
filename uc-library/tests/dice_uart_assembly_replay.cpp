#include "presonus/dice/uart_assembly.hpp"
#include <algorithm>
#include <climits>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
presonus::dice::UartAssemblyState *current;
std::ostringstream events;
unsigned clockIndex;
const long long ticks[] = {-1000001, 2999999, -3999999, LLONG_MAX, LLONG_MIN,
                           0,        1000000, -999999,  999999};
std::string hex(const unsigned char *p, unsigned n) {
  std::ostringstream s;
  s << std::hex << std::setfill('0');
  for (unsigned i = 0; i < n; ++i)
    s << std::setw(2) << unsigned(p[i]);
  return s.str();
}
std::vector<unsigned char> unhex(const std::string &s) {
  std::vector<unsigned char> b;
  if (s == "-")
    return b;
  for (unsigned i = 0; i < s.size(); i += 2)
    b.push_back(std::stoul(s.substr(i, 2), nullptr, 16));
  return b;
}
void packet(const Presonus::DICE::SysexPacket &p) {
  const auto &m = p.portableMetadata();
  events << unsigned(p.length) << ':' << hex(p.bytes.data(), 255) << ':';
  for (auto v : m.headerWords)
    events << v << ',';
  events << ':' << m.constructedQuotient << ':';
  for (auto v : m.trailingWords)
    events << v << ',';
}
class Callbacks : public presonus::dice::AssemblyCallbacks {
public:
  void noReceiver(unsigned type) override { events << "W" << type << ';'; }
  void packetLog(const Presonus::DICE::SysexPacket &p) override {
    events << "P";
    packet(p);
    events << ';';
  }
  void sourcePortError(presonus::dice::AssemblyError e, unsigned v) override {
    events << "E" << unsigned(e) << ':' << v << ';';
  }
};
class Receiver : public Presonus::DICE::ISysexReceiver {
public:
  int id = 0;
  bool accept = false;
  int action = 0;
  Receiver *all = nullptr;
  bool accepts(const Presonus::DICE::SysexPacket &p) override {
    events << "A" << id << ':';
    packet(p);
    events << ';';
    if (action == 1)
      current->receivers.add(all + 3);
    if (action == 2)
      current->receivers.at(0) = all + 1;
    if (action == 3)
      current->receivers.at(1) = all + 3;
    action = 0;
    return accept;
  }
  void receive(const Presonus::DICE::SysexPacket &p) override {
    events << "R" << id << ':';
    packet(p);
    events << ';';
  }
};
} // namespace

namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  const auto value = ticks[clockIndex++ % 9];
  events << "C" << unsigned(current->count) << ':'
         << unsigned(current->span()[64]) << ':' << value << ';';
  return value;
}
} // namespace presonus::dice

int main() {
  unsigned total;
  std::cin >> total;
  for (unsigned caseIndex = 0; caseIndex < total; ++caseIndex) {
    std::string name, seedHex;
    unsigned count, receiverCount, mask, action, chunks;
    std::cin >> name >> seedHex >> count >> receiverCount >> mask >> action >>
        chunks;
    auto seedVector = unhex(seedHex);
    if (seedVector.size() != 67 || receiverCount > 3)
      return 2;
    std::array<unsigned char, 67> seed;
    std::copy(seedVector.begin(), seedVector.end(), seed.begin());
    presonus::dice::UartAssemblyState state(seed, count, 16);
    current = &state;
    Callbacks callbacks;
    Presonus::DICE::Dice3Uart uart(state, callbacks);
    Receiver receivers[4];
    for (int i = 0; i < 4; ++i) {
      receivers[i].id = i;
      receivers[i].accept = (mask & (1u << i)) != 0;
      receivers[i].all = receivers;
    }
    receivers[0].action = action;
    for (unsigned i = 0; i < receiverCount; ++i)
      state.receivers.add(receivers + i);
    events.str("");
    events.clear();
    clockIndex = 0;
    for (unsigned chunk = 0; chunk < chunks; ++chunk) {
      int length;
      std::string dataHex;
      std::cin >> length >> dataHex;
      auto data = unhex(dataHex);
      if (length > int(data.size()))
        return 3;
      uart.assembleSYSEX(data.empty() ? nullptr : data.data(), length);
      events << "S" << unsigned(state.count) << ':' << hex(state.span(), 67)
             << ':' << unsigned(state.error) << ':'
             << state.rejectedUnsafeWrites << ':' << state.receivers.count()
             << ';';
    }
    std::cout << name << ' ' << events.str() << '\n';
  }
}
