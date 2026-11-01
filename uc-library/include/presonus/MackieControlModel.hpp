#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <vector>
namespace Presonus {
// Intentional portable source port. Field layout and unencoded original return
// declarations are unresolved; these callbacks are independent boundary
// adapters.
class MackieControlModel {
public:
  struct Entry {
    int tag;
    int note;
    int stateIndex;
  };
  std::vector<Entry> entries;
  std::vector<unsigned char> buttonStates;
  std::array<unsigned char, 9> touched{};
  std::array<std::int32_t, 9> faderValues{};
  bool omitMaster{};
  std::function<void(const unsigned char *, unsigned int, unsigned int)>
      midiSink;
  std::function<void(int, bool)> buttonRelease;
  std::function<void(int, bool)> faderRelease;
  std::function<void(int, bool)> ledSink;
  void sendMidiMessage(const unsigned char *, unsigned int);
  bool setButtonState(int, bool);
  void releaseAllButtons();
  void resetLeds();
  void touchFader(int, bool);
};
} // namespace Presonus
