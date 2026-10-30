#include "dice_fixture_receivers.hpp"
#include "presonus/dice/sysex.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace Presonus::DICE;
using State = presonus::dice::SubsystemState;
std::string hex(std::uint64_t word, unsigned width) {
  constexpr const char *digits = "0123456789abcdef";
  std::string out(width, '0');
  for (unsigned i = 0; i < width; ++i) {
    out[width - i - 1] = digits[word & 15];
    word >>= 4;
  }
  return out;
}
template <std::size_t N>
std::array<unsigned char, N> unhex(const std::string &text) {
  if (text.size() != N * 2)
    throw std::runtime_error("hex width");
  std::array<unsigned char, N> out{};
  for (unsigned i = 0; i < N; ++i)
    out[i] = static_cast<unsigned char>(
        std::stoul(text.substr(i * 2, 2), nullptr, 16));
  return out;
}
std::string dataHex(const SysexPacket &packet) {
  std::string out;
  for (unsigned i = 0; i < 255; ++i)
    out += hex(packet.bytes[i], 2);
  return out;
}
std::int64_t signed64(std::uint64_t word) {
  std::int64_t value;
  std::memcpy(&value, &word, 8);
  return value;
}
std::uint64_t bits64(std::int64_t value) {
  std::uint64_t word;
  std::memcpy(&word, &value, 8);
  return word;
}
int signed32(std::uint32_t word) {
  int value;
  std::memcpy(&value, &word, 4);
  return value;
}
struct ClockContext {
  std::array<std::uint64_t, 2> ticks{};
  unsigned index = 0;
  std::vector<std::string> events;
};
ClockContext *clockContext = nullptr;
namespace presonus::dice {
std::int64_t packetClockRawTicks() {
  if (!clockContext || clockContext->index >= 2)
    throw std::runtime_error("clock contract exceeded");
  const auto word = clockContext->ticks[clockContext->index++];
  clockContext->events.push_back("C:" + hex(word, 16));
  return signed64(word);
}
} // namespace presonus::dice
bool equal(const State &a, const State &b) {
  return a.command == b.command && a.status == b.status &&
         a.infoWords == b.infoWords && a.rateWord == b.rateWord &&
         a.clockWord == b.clockWord;
}
bool readState(std::istream &input, State &state) {
  unsigned command, status;
  if (!(input >> command >> status >> state.infoWords[0] >>
        state.infoWords[1] >> state.infoWords[2] >> state.rateWord >>
        state.clockWord))
    return false;
  state.command = static_cast<unsigned char>(command);
  state.status = static_cast<unsigned char>(status);
  return true;
}
struct Services : presonus::dice::SubsystemServices {
  ClockContext *clock = nullptr;
  std::uint32_t ackWord = 0;
  unsigned char ackStatus = 0;
  void post(SysexPacket &packet) override {
    const auto &meta = packet.portableMetadata();
    if (meta.headerWords != std::array<std::uint32_t, 2>{} ||
        meta.trailingWords != std::array<std::uint32_t, 4>{})
      throw std::runtime_error("packet metadata zero fields");
    clock->events.push_back("P:" + hex(packet.length, 2) + ":" +
                            dataHex(packet) + ":" +
                            hex(bits64(meta.constructedQuotient), 16));
  }
  std::uint32_t waitAck(Dice3Subsystem &receiver,
                        std::int64_t timeout) override {
    clock->events.push_back("W:" + hex(bits64(timeout), 16));
    receiver.portableState().status = ackStatus;
    return ackWord;
  }
};
unsigned constructorTests(std::istream &input) {
  unsigned length, cases = 0;
  std::string sourceText, wantedData;
  std::uint64_t first, second, wantedTime;
  while (input >> std::hex >> length >> sourceText >> first >> second >>
         wantedData >> wantedTime) {
    auto source = unhex<255>(sourceText);
    const auto before = source;
    ClockContext clock;
    clock.ticks = {first, second};
    clockContext = &clock;
    SysexPacket packet(source.data(), static_cast<unsigned char>(length));
    if (clock.index != 2 ||
        clock.events != std::vector<std::string>{"C:" + hex(first, 16),
                                                 "C:" + hex(second, 16)} ||
        packet.length != length || dataHex(packet) != wantedData ||
        bits64(packet.portableMetadata().constructedQuotient) != wantedTime ||
        source != before)
      throw std::runtime_error("original constructor semantic mismatch");
    if (packet.bytes[255] != 0)
      throw std::runtime_error("portable inactive tail initialization");
    if (packet.portableMetadata().headerWords !=
            std::array<std::uint32_t, 2>{} ||
        packet.portableMetadata().trailingWords !=
            std::array<std::uint32_t, 4>{})
      throw std::runtime_error("constructor zero metadata");
    ++cases;
  }
  if (!input.eof() || !cases)
    throw std::runtime_error("constructor fixture parse");
  return cases;
}
unsigned commandTests(std::istream &input) {
  char op;
  unsigned cases = 0;
  while (input >> op) {
    std::array<std::uint32_t, 4> args{};
    State before, after;
    ClockContext clock;
    Services services;
    unsigned status, events;
    std::uint32_t wanted;
    if (!(input >> std::hex >> args[0] >> args[1] >> args[2] >> args[3]) ||
        !readState(input, before) ||
        !(input >> clock.ticks[0] >> clock.ticks[1] >> services.ackWord >>
          status >> wanted) ||
        !readState(input, after) || !(input >> events))
      throw std::runtime_error("command fixture header");
    services.clock = &clock;
    services.ackStatus = static_cast<unsigned char>(status);
    clockContext = &clock;
    Dice3Subsystem subsystem(presonus::dice::BorrowedSubsystemSetup{});
    subsystem.portableState() = before;
    subsystem.setPortableServices(services);
    std::int32_t result;
    switch (op) {
    case 'U':
      result = subsystem.uiSetCmd(signed32(args[0]), signed32(args[1]));
      break;
    case 'R':
      result =
          subsystem.setRate(static_cast<Dice3SampleRate>(signed32(args[0])));
      break;
    case 'C':
      result = subsystem.setClockSource(
          static_cast<Dice3ClockSource>(signed32(args[0])));
      break;
    case 'T':
      result = subsystem.setRoute(
          static_cast<Dice3AudioSinkDevice>(signed32(args[0])),
          static_cast<Dice3AudioSink>(signed32(args[1])),
          static_cast<Dice3AudioSourceDevice>(signed32(args[2])),
          static_cast<Dice3AudioSource>(signed32(args[3])));
      break;
    default:
      throw std::runtime_error("command operation");
    }
    std::vector<std::string> wantedEvents(events);
    for (auto &event : wantedEvents)
      if (!(input >> event))
        throw std::runtime_error("missing event");
    if (static_cast<std::uint32_t>(result) != wanted ||
        !equal(subsystem.portableState(), after) ||
        clock.events != wantedEvents) {
      std::cerr << op << " case=" << std::dec << cases
                << " expected=" << std::hex << wanted
                << " actual=" << static_cast<std::uint32_t>(result)
                << " events=" << clock.events.size() << '\n';
      throw std::runtime_error("original command/state/ordered-event mismatch");
    }
    ++cases;
  }
  if (!input.eof() || !cases)
    throw std::runtime_error("command fixture parse");
  return cases;
}
unsigned receiverTests(std::istream &input) {
  char op;
  unsigned length, cases = 0;
  std::string data;
  while (input >> op >> std::hex >> length >> data) {
    State before, after;
    if (!readState(input, before) || !readState(input, after))
      throw std::runtime_error("receiver fixture header");
    SysexPacket packet;
    packet.bytes = unhex<256>(data);
    packet.length = static_cast<unsigned char>(length);
    const auto original = packet.bytes;
    if (op == 'B') {
      presonus::dice::fixture::ConcreteReceiver receiver;
      receiver.portableState() = before;
      receiver.receive(packet);
      if (!equal(receiver.portableState(), after))
        throw std::runtime_error("base receiver state");
    } else if (op == 'S') {
      Dice3Subsystem receiver(presonus::dice::BorrowedSubsystemSetup{});
      receiver.portableState() = before;
      receiver.receive(packet);
      if (!equal(receiver.portableState(), after))
        throw std::runtime_error("subsystem receiver state");
    } else
      throw std::runtime_error("receiver operation");
    if (packet.bytes != original || packet.length != length)
      throw std::runtime_error("receiver changed packet");
    ++cases;
  }
  if (!input.eof() || !cases)
    throw std::runtime_error("receiver fixture parse");
  return cases;
}
int main(int argc, char **argv) {
  try {
    if (argc != 3)
      throw std::runtime_error("mode and fixture path required");
    std::ifstream input(argv[2]);
    if (!input)
      throw std::runtime_error("fixture open failed");
    const std::string mode = argv[1];
    unsigned count;
    if (mode == "constructor")
      count = constructorTests(input);
    else if (mode == "commands")
      count = commandTests(input);
    else if (mode == "receivers")
      count = receiverTests(input);
    else
      throw std::runtime_error("unknown mode");
    std::cout
        << "PASS: " << mode << ' ' << count
        << " candidate fixture cases; no active-header or readiness changes\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
