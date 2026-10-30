// Serial setup adapted from lpc21isp.c, Martin Maurer 2003-2014,
// portions Aeolus Development 2004. LGPL-3.0-or-later; see LICENSES/.
// Original application member/state/error handling is an explicit source port.
#include "core/system/coredebug.h"
#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
namespace Presonus {
int LPCProgrammer::openPort(const char *path) {
  inputState.descriptor = ::open(path, O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (inputState.descriptor < 0) {
    int error = errno;
    Core::DebugPrintf("Can't open COM-Port %s ! (Error: %dd (0x%X))\n", path,
                      error, error);
    return 0;
  }
  termios previous;
  ::tcgetattr(inputState.descriptor, &previous);
  termios settings;
  std::memset(&settings, 0, sizeof(settings));
  settings.c_cflag = B115200 | CS8 | CLOCAL | CREAD;
  // Matching upstream setup statements, expressed using actual host POSIX
  // fields.
  settings.c_iflag = IGNPAR | IGNBRK | IXON | IXOFF;
  settings.c_oflag = 0;
  settings.c_lflag = 0;
  ::cfmakeraw(&settings);
  settings.c_cc[VTIME] = 1;
  settings.c_cc[VMIN] = 0;
  ::tcflush(inputState.descriptor, TCIFLUSH);
  if (::tcsetattr(inputState.descriptor, TCSANOW, &settings) == 0)
    return 1;
  Core::DebugPrintf(
      "Could not change serial port behaviour (wrong baudrate?)\n");
  return 0;
}
int LPCProgrammer::writeChar(unsigned char value) {
  return static_cast<int>(::write(inputState.descriptor, &value, 1));
}
int LPCProgrammer::close() {
  int result = ::close(inputState.descriptor);
  inputState.descriptor = 0;
  return result;
}
} // namespace Presonus
