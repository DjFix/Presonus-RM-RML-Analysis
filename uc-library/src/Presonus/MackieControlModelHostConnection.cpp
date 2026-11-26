#include "presonus/MackieControlModel.hpp"
#include <cstdlib>
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
// Provisional void returns: the ordinary original return declarations are
// unresolved.
void MackieControlModel::sendHostConnectionQueryAlternative() {
  for (auto &byte : hostConnectionChallenge)
    byte = static_cast<unsigned char>(std::rand() & 0x7f);
  unsigned char message[14]{0xf0, 0, 0, 0x66, hostConnectionIdentity[0], 0x1b};
  for (unsigned i = 1; i != 8; ++i)
    message[5 + i] = hostConnectionIdentity[i] & 0x7f;
  message[13] = 0xf7;
  sendMidiMessage(message, sizeof message);
}
void MackieControlModel::sendHostConnectionQuery() {
  for (auto &byte : hostConnectionChallenge)
    byte = static_cast<unsigned char>(std::rand() & 0x7f);
  unsigned char message[18]{0xf0, 0, 0, 0x66, hostConnectionIdentity[0], 1};
  for (unsigned i = 1; i != 8; ++i)
    message[5 + i] = hostConnectionIdentity[i] & 0x7f;
  for (unsigned i = 0; i != 4; ++i)
    message[13 + i] = hostConnectionChallenge[i] & 0x7f;
  message[17] = 0xf7;
  sendMidiMessage(message, sizeof message);
}
} // namespace Presonus
