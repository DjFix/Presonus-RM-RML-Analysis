#include "presonus/surface/UCMidiInputAdapter.hpp"
#include <cstdint>
#include <iostream>
#include <vector>

namespace {
class Sink final : public Presonus::IMidiSink {
public:
  const unsigned char *original{};
  void sendMidiMessage(const unsigned char *data, unsigned length,
                       unsigned port) override {
    std::cout << length << ' ' << port << ' ' << (data == original);
    for (unsigned i = 0; i < length; ++i)
      std::cout << ' ' << static_cast<unsigned>(data[i]);
    std::cout << '\n';
  }
};
} // namespace

int main() {
  std::uint32_t word;
  unsigned length;
  while (std::cin >> word >> length) {
    std::vector<unsigned char> payload;
    for (unsigned i = 0; i < length; ++i) {
      unsigned byte;
      if (!(std::cin >> byte) || byte > 255)
        return 1;
      payload.push_back(static_cast<unsigned char>(byte));
    }
    Sink sink;
    sink.original = payload.data();
    Presonus::Surface::UCMidiInputAdapter adapter(sink);
    Presonus::UC::IMidiEventHandler &handler = adapter;
    Presonus::UC::MidiEvent event;
    event.messageWord = word;
    event.sysexData = payload.data();
    event.sysexLength = static_cast<std::uint16_t>(length);
    handler.handleMidiEvent(event);
  }
  return std::cin.eof() ? 0 : 1;
}
