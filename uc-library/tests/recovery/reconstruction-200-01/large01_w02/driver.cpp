#include "presonus/FaderUnitComponent.hpp"
#include "presonus/IFaderPanel.hpp"
#include "presonus/MackieControlComponent.hpp"
#include "presonus/MackieControlExtender.hpp"
#include "presonus/surface/AudioUtilitiesPage.hpp"
#include "presonus/surface/FaderUtilitiesPage.hpp"
#include "presonus/surface/StartPageComponent.hpp"
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>
struct Panel final : Presonus::IFaderPanel {
  std::uint32_t payload = 0xa5a5a5a5;
  inline static unsigned deleteCalls{};
  static void operator delete(void *p) {
    ++deleteCalls;
    ::operator delete(p);
  }
};
static_assert(std::is_abstract<Presonus::IFaderPanel>::value,
              "Partial panel stays abstract");
struct MidiSink final : Presonus::IMidiSink {
  std::vector<unsigned> &bytes;
  explicit MidiSink(std::vector<unsigned> &bytes) : bytes(bytes) {}
  void sendMidiMessage(const unsigned char *p, unsigned n,
                       unsigned port) override {
    if (port != 0)
      std::abort();
    bytes.assign(p, p + n);
  }
};
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    int task;
    std::int64_t a = 0, b = 0, c = 1;
    in >> task >> a >> b >> c;
    Presonus::MackieControlModel m;
    std::vector<unsigned> midi;
    m.midiSink = [&](const unsigned char *p, unsigned n, unsigned port) {
      if (port != 0)
        std::abort();
      midi.assign(p, p + n);
    };
    MidiSink actualSink(midi);
    if (task == 2 || task == 7)
      m.setMidiSink(task == 2 && c == 0 ? nullptr : &actualSink, 99);
    std::vector<std::uint64_t> out;
    switch (task) {
    case 1:
      m.setVersionString(
          reinterpret_cast<const char *>(static_cast<std::uintptr_t>(a)));
      out = {reinterpret_cast<std::uintptr_t>(m.versionString)};
      break;
    case 2:
      m.turnEncoder(static_cast<int>(a), static_cast<int>(b));
      out.assign(midi.begin(), midi.end());
      break;
    case 3:
      out = {static_cast<unsigned>(m.faderTagToIndex(static_cast<int>(a)))};
      break;
    case 4:
      m.setMidiSink(reinterpret_cast<Presonus::IMidiSink *>(
                        static_cast<std::uintptr_t>(a)),
                    static_cast<int>(b));
      out = {reinterpret_cast<std::uintptr_t>(m.applicationMidiSink)};
      break;
    case 5:
      m.setPanel(reinterpret_cast<Presonus::IFaderPanel *>(
          static_cast<std::uintptr_t>(a)));
      out = {reinterpret_cast<std::uintptr_t>(m.panel)};
      break;
    case 6:
      out = {static_cast<unsigned>(m.encoderTagToIndex(static_cast<int>(a)))};
      break;
    case 7: {
      m.faderValues.fill(static_cast<std::int32_t>(c));
      auto bits = static_cast<std::uint32_t>(b);
      float value;
      std::memcpy(&value, &bits, 4);
      m.moveFader(static_cast<int>(a), value);
      for (auto v : m.faderValues)
        out.push_back(static_cast<std::uint32_t>(v));
      out.push_back(!midi.empty());
      out.insert(out.end(), midi.begin(), midi.end());
      break;
    }
    case 8:
      m.setAcceptMCUSysex(a != 0);
      out = {m.acceptMCUSysex};
      break;
    case 9: {
      alignas(Panel) unsigned char storage[sizeof(Panel)];
      auto *p = new (storage) Panel;
      const auto payloadOffset =
          reinterpret_cast<unsigned char *>(&p->payload) - storage;
      Panel::deleteCalls = 0;
      p->Presonus::IFaderPanel::~IFaderPanel();
      std::uint32_t payload;
      std::memcpy(&payload, storage + payloadOffset, 4);
      out = {Panel::deleteCalls, payload == 0xa5a5a5a5};
      break;
    }
    case 10: {
      Presonus::MackieControlComponent component;
      auto *p = component.getModel();
      p->setAcceptMCUSysex(true);
      out = {p == &component.model && component.model.acceptMCUSysex ? 136u
                                                                     : 0u};
      break;
    }
    default:
      return 3;
    }
    for (std::size_t i = 0; i < out.size(); ++i)
      std::cout << (i ? " " : "") << out[i];
    std::cout << "\n";
  }
}
