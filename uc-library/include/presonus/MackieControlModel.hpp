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
  // Independent portable counterpart of the native MIDI-sorted lookup table.
  std::vector<Entry> midiEntries;
  std::vector<unsigned char> buttonStates;
  std::array<unsigned char, 9> touched{};
  std::array<std::int32_t, 9> faderValues{};
  bool omitMaster{};
  std::function<void(const unsigned char *, unsigned int, unsigned int)>
      midiSink;
  std::function<void(int, bool)> buttonRelease;
  std::function<void(int, bool)> faderRelease;
  std::function<void(int, bool)> ledSink;
  static int compareEntryMidiNotes(const void *, const void *);
  static int compareEntryTags(const void *, const void *);
  // Required independent application boundary adapters; original provider type
  // and virtual declarations are unresolved. No Core substitute is defined.
  std::function<void()> connectionInitializer;
  std::function<void(int, const char *)> textSink;
  std::function<void(int, float)> faderValueSink;
  unsigned connectionState{};
  std::array<char, 3> assignmentData{};
  std::array<char, 11> timecodeData{};
  void addMapping(int, int);
  // Independent source-port bytes corresponding to observed native reads.
  std::array<unsigned char, 8> hostConnectionIdentity{};
  void sendHostConnectionConfirmation(bool);
  void initConnection();
  void updateAssignmentData();
  void updateTimecodeData();
  void onMessageFaderValue(int, float);
  Entry *getEntryByMidiNote(int);
  Entry *getEntryByTag(int);
  void turnScrubwheel(int);
  void sendMidiMessage(const unsigned char *, unsigned int);
  bool setButtonState(int, bool);
  void releaseAllButtons();
  void resetLeds();
  void touchFader(int, bool);
};
} // namespace Presonus
