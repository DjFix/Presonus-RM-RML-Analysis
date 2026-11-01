#include "presonus/MackieControlModel.hpp"
namespace Presonus {
void MackieControlModel::sendMidiMessage(const unsigned char *data,
                                         unsigned int size) {
  if (midiSink)
    midiSink(data, size, 0);
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
