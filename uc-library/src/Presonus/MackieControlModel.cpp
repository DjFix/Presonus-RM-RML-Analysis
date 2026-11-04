#include "presonus/MackieControlModel.hpp"
namespace Presonus {
void MackieControlModel::sendMidiMessage(const unsigned char *data,
                                         unsigned int size) {
  if (applicationMidiSinkConfigured) {
    if (applicationMidiSink)
      applicationMidiSink->sendMidiMessage(data, size, 0);
  } else if (midiSink) {
    midiSink(data, size, 0);
  }
}
bool MackieControlModel::setButtonState(int tag, bool state) {
  const Entry *entry = nullptr;
  for (const auto &candidate : entries)
    if (candidate.tag == tag) {
      entry = &candidate;
      break;
    }
  if (!entry)
    return false;
  if (entry->note < 0 || entry->stateIndex < 0)
    return true;
  auto &cached = buttonStates[static_cast<unsigned>(entry->stateIndex)];
  if (cached == state)
    return true;
  cached = state;
  const unsigned char bytes[]{0x90, static_cast<unsigned char>(entry->note),
                              static_cast<unsigned char>(state ? 127 : 0)};
  sendMidiMessage(bytes, 3);
  return true;
}
void MackieControlModel::releaseAllButtons() {
  for (std::size_t i = 0; i < entries.size(); ++i)
    buttonRelease(entries[i].tag, false);
  for (int tag = 0x2000; tag != 0x2008; ++tag)
    faderRelease(tag, false);
  if (!omitMaster)
    faderRelease(0x9000, false);
}
void MackieControlModel::resetLeds() {
  for (std::size_t i = 0; i < entries.size(); ++i)
    ledSink(entries[i].tag, false);
}
void MackieControlModel::touchFader(int tag, bool state) {
  const auto difference = static_cast<std::uint32_t>(tag) - 0x2000u;
  const auto nonnegative = (difference & 0x80000000u) ? 0u : difference;
  const unsigned index =
      tag == 0x9000 ? 8u : (nonnegative < 7 ? nonnegative : 7u);
  if (!state)
    faderValues[index] = -1;
  if (state ? touched[index] != 0 : touched[index] == 0)
    return;
  touched[index] = state;
  const unsigned char bytes[]{0x90, static_cast<unsigned char>(0x68 + index),
                              static_cast<unsigned char>(state ? 127 : 0)};
  sendMidiMessage(bytes, 3);
}
} // namespace Presonus

#include "presonus/MackieControlModel.hpp"
#include <algorithm>
#include <cstdlib>
#include <cstring>
namespace Presonus {
// Portable declaration choices: int comparator results match observed ARM r0.
// Static comparators are called by libc with two entry pointers, without this.
int MackieControlModel::compareEntryMidiNotes(const void *a, const void *b) {
  const auto x = static_cast<const Entry *>(a)->note;
  const auto y = static_cast<const Entry *>(b)->note;
  return x == y ? 0 : (x < y ? -1 : 1);
}
int MackieControlModel::compareEntryTags(const void *a, const void *b) {
  const auto x = static_cast<const Entry *>(a)->tag;
  const auto y = static_cast<const Entry *>(b)->tag;
  return x == y ? 0 : (x < y ? -1 : 1);
}
void MackieControlModel::addMapping(int tag, int note) {
  const int index = static_cast<int>(buttonStates.size());
  if (buttonStates.size() <= 109)
    buttonStates.push_back(0);
  const Entry entry{tag, note, index};
  if (note >= 0) {
    if (midiEntries.size() <= 109)
      midiEntries.push_back(entry);
    std::qsort(midiEntries.data(), midiEntries.size(), sizeof(Entry),
               compareEntryMidiNotes);
  }
  if (tag >= 0) {
    if (entries.size() <= 109)
      entries.push_back(entry);
    std::qsort(entries.data(), entries.size(), sizeof(Entry), compareEntryTags);
  }
}
void MackieControlModel::initConnection() {
  if (connectionState == 4)
    return;
  connectionInitializer();
  connectionState = 1;
}
void MackieControlModel::updateAssignmentData() {
  assignmentData[2] = 0;
  textSink(0xa006, assignmentData.data());
}
void MackieControlModel::updateTimecodeData() {
  timecodeData[10] = 0;
  textSink(0xa007, timecodeData.data());
}
void MackieControlModel::onMessageFaderValue(int index, float value) {
  if (static_cast<unsigned>(index) > 8 || touched[static_cast<unsigned>(index)])
    return;
  faderValueSink(index == 8 ? 0x9000 : index + 0x2000, value);
}
MackieControlModel::Entry *MackieControlModel::getEntryByMidiNote(int note) {
  const Entry key{0, note, -1};
  if (midiEntries.empty())
    return nullptr;
  return static_cast<Entry *>(std::bsearch(&key, midiEntries.data(),
                                           midiEntries.size(), sizeof(Entry),
                                           compareEntryMidiNotes));
}
MackieControlModel::Entry *MackieControlModel::getEntryByTag(int tag) {
  const Entry key{tag, 0, -1};
  if (entries.empty())
    return nullptr;
  return static_cast<Entry *>(std::bsearch(&key, entries.data(), entries.size(),
                                           sizeof(Entry), compareEntryTags));
}
void MackieControlModel::turnScrubwheel(int direction) {
  if (direction == 0)
    return;
  const unsigned char message[]{
      0xb0, 0x3c, static_cast<unsigned char>(direction < 0 ? 0x41 : 1)};
  sendMidiMessage(message, 3);
}
} // namespace Presonus
