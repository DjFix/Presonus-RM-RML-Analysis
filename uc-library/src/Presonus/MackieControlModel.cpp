#include "core/public/corestringbuffer.h"
#include "presonus/IFaderPanel.hpp"
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
  addMapping(MappingEntry{tag, note, -1});
}
void MackieControlModel::addMapping(const MappingEntry &mapping) {
  constexpr std::size_t capacity = 110;
  MappingEntry entry = mapping;
  if (entry.stateIndex < 0) {
    entry.stateIndex = static_cast<int>(buttonStates.size());
    if (buttonStates.size() < capacity)
      buttonStates.push_back(0);
  }
  if (entry.note >= 0) {
    if (midiEntries.size() < capacity)
      midiEntries.push_back(entry);
    std::qsort(midiEntries.data(), midiEntries.size(), sizeof(Entry),
               compareEntryMidiNotes);
  }
  if (entry.tag >= 0) {
    if (entries.size() < capacity)
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
  const int tag = index == 8 ? 0x9000 : index + 0x2000;
  if (faderValueSink)
    faderValueSink(tag, value);
  else if (auto *updates = panel ? panel->localUpdates() : nullptr)
    updates->updateFader(tag, value);
}

void MackieControlModel::onMessageMeter(int channel, int level) {
  if (static_cast<unsigned>(channel) >= meterPeaks.size())
    return;
  auto *updates = panel ? panel->localUpdates() : nullptr;
  float value;
  if (level == 14 || level == 15) {
    const bool clipped = level == 14;
    if (updates)
      updates->updateLedState(0x4000 + channel, clipped);
    value = clipped ? 1.f : 0.f;
  } else {
    value = static_cast<float>(level) * 0x1.3b13b2p-4f;
  }
  auto &peak = meterPeaks[static_cast<unsigned>(channel)];
  if (peak < value) {
    peak = value;
    if (updates)
      updates->updateMeter(channel, value);
  }
}

void MackieControlModel::onMessageVPotRing(int channel, int ring) {
  if (static_cast<unsigned>(channel) >= 8)
    return;
  auto *updates = panel ? panel->localUpdates() : nullptr;
  if (!updates)
    return;
  int mode = 0;
  float value = 0.f;
  if (ring != 0) {
    switch (ring & 0x30) {
    case 0:
      mode = 1;
      break;
    case 0x10:
      mode = 3;
      break;
    }
    value = static_cast<float>((ring & 0xf) - 1) / 10.f;
  }
  updates->updateValueBar(0x4300 + channel, mode, value, (ring & 0x40) != 0);
}

void MackieControlModel::resetFaders() {
  const int count = omitMaster ? 8 : 9;
  for (int channel = 0; channel < count; ++channel)
    onMessageFaderValue(channel, 0.f);
  for (int channel = 0; channel < 8; ++channel)
    touchFader(0x2000 + channel, false);
  if (!omitMaster)
    touchFader(0x9000, false);
}

void MackieControlModel::updateDisplayData() {
  auto *updates = panel ? panel->localUpdates() : nullptr;
  if (!updates)
    return;

  for (int column = 0; column < 8; ++column) {
    Core::CString32 top;
    Core::CString32 bottom;
    for (int offset = 0; offset < 7; ++offset) {
      const int index = column * 7 + offset;
      top.append(displayData[index]);
      bottom.append(displayData[56 + index]);
    }
    updates->updateTextDisplay(0x4700 + column, top, 0);
    updates->updateTextDisplay(0x4800 + column, bottom, 0);
  }
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
