#include "presonus/surface/UCMidiInputAdapter.hpp"
#include <cstdio>

#include "presonus/IFaderUnit.hpp"
#include <array>

namespace Presonus::Surface {
struct UCMidiInputAdapterReplayAccess {
  static IFaderUnit *fader(const UCMidiInputAdapter &input) {
    return input.faderUnit_;
  }
};
} // namespace Presonus::Surface

class Sink : public Presonus::IMidiSink {
public:
  void sendMidiMessage(const unsigned char *data, unsigned size,
                       unsigned port) override {
    ++calls;
    valid = valid && size == 3 && port == 0 && data[0] == 0x90 &&
            data[1] == 0x31 && data[2] == 0x7f;
  }
  unsigned calls = 0;
  bool valid = true;
};

int main() {
  using namespace Presonus;
  using namespace Presonus::Surface;
  Sink sink;
  UCMidiInputAdapter input(sink);
  IFaderUnit first(IFaderUnit::SourcePortTag{});
  IFaderUnit second(IFaderUnit::SourcePortTag{});
  IFaderUnit *const values[] = {nullptr, &first, &second};
  const auto code = [&](const IFaderUnit *pointer) {
    return pointer == nullptr   ? 0u
           : pointer == &first  ? 1u
           : pointer == &second ? 2u
                                : 3u;
  };
  const unsigned sequence[] = {1, 2, 0, 1};
  for (unsigned index : sequence) {
    const auto before = code(UCMidiInputAdapterReplayAccess::fader(input));
    const auto calls = sink.calls;
    input.setFaderUnit(values[index]);
    if (sink.calls != calls)
      return 2;
    UC::MidiEvent event{};
    event.messageWord = 0x7f3190;
    input.handleMidiEvent(event);
    if (sink.calls != calls + 1 || !sink.valid)
      return 3;
    std::printf("%u %u %u\n", index, before,
                code(UCMidiInputAdapterReplayAccess::fader(input)));
  }
}
