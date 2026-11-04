#include "presonus/reconstruction200/large01_w02.hpp"
#include "presonus/frontier01/frontier01_w04.hpp"
#include <cstdint>
#include <limits>
namespace Presonus {
void MackieControlModel::setVersionString(const char *value) {
  versionString = value;
}
void MackieControlModel::setMidiSink(IMidiSink *value, int) {
  applicationMidiSink = value;
  applicationMidiSinkConfigured = true;
}
void MackieControlModel::setPanel(IFaderPanel *value) { panel = value; }
void MackieControlModel::setAcceptMCUSysex(bool value) {
  acceptMCUSysex = value;
}
int MackieControlModel::encoderTagToIndex(int tag) const {
  const auto difference = static_cast<std::uint32_t>(tag) - 0x2000u;
  const auto nonnegative = difference & 0x80000000u ? 0u : difference;
  return static_cast<int>(nonnegative < 7 ? nonnegative : 7u);
}
int MackieControlModel::faderTagToIndex(int tag) const {
  return tag == 0x9000 ? 8 : encoderTagToIndex(tag);
}
void MackieControlModel::turnEncoder(int tag, int delta) {
  // Preserve ARM32 wrapping negate, including INT_MIN, without signed overflow.
  auto magnitude = delta < 0 ? 0u - static_cast<std::uint32_t>(delta)
                             : static_cast<std::uint32_t>(delta);
  if (!(magnitude & 0x80000000u) && magnitude >= 63u)
    magnitude = 63u;
  const unsigned char bytes[]{
      0xb0, static_cast<unsigned char>(0x10 + encoderTagToIndex(tag)),
      static_cast<unsigned char>(delta < 0 ? magnitude : magnitude | 0x40u)};
  sendMidiMessage(bytes, 3);
}
void MackieControlModel::moveFader(int tag, float value) {
  const auto index = static_cast<unsigned>(faderTagToIndex(tag));
  const float scaled = value * 16368.0f;
  // The bounded replay covers normalized finite inputs. Saturation makes the
  // independent source port defined outside that domain; it is not ABI proof.
  const std::uint32_t position = !(scaled > 0.0f) ? 0u
                                 : scaled >= 4294967296.0f
                                     ? std::numeric_limits<std::uint32_t>::max()
                                     : static_cast<std::uint32_t>(scaled);
  if (static_cast<std::uint32_t>(faderValues[index]) == position)
    return;
  faderValues[index] = static_cast<std::int32_t>(position);
  const unsigned char bytes[]{
      static_cast<unsigned char>(0xe0u | index),
      static_cast<unsigned char>(position & 0x7f),
      static_cast<unsigned char>((position >> 7) & 0x7f)};
  sendMidiMessage(bytes, 3);
}
IFaderPanel::~IFaderPanel() {}
MackieControlModel *MackieControlComponent::getModel() { return &model; }
} // namespace Presonus
