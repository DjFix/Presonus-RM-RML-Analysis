#include "presonus/MackieControlModel.hpp"
namespace Presonus {
void MackieControlModel::sendHostConnectionConfirmation(bool accepted) {
  unsigned char message[14]{0xf0,
                            0,
                            0,
                            0x66,
                            hostConnectionIdentity[0],
                            static_cast<unsigned char>(accepted ? 3 : 4)};
  for (unsigned i = 1; i != 8; ++i)
    message[5 + i] = hostConnectionIdentity[i] & 0x7f;
  message[13] = 0xf7;
  sendMidiMessage(message, sizeof message);
}
} // namespace Presonus
