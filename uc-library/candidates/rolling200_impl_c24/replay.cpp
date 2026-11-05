#include "presonus/panel/SharedMemoryComm.hpp"
#include "presonus/panel/uart_message.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  if (!input)
    return 3;
  unsigned op, seed, expected, unchanged;
  int length;
  unsigned cases = 0;
  while (input >> op >> seed >> length >> expected >> unchanged) {
    Presonus::Panel::SharedMemoryComm value;
    std::array<char, 64> buffer;
    for (unsigned i = 0; i < buffer.size(); ++i)
      buffer[i] = static_cast<char>((seed + i * 17) & 255);
    const auto before = buffer;
    Uart_Msg_Type message;
    for (unsigned i = 0; i < message.bytes.size(); ++i)
      message.bytes[i] = static_cast<unsigned char>((seed + i * 17) & 255);
    const auto oldMessage = message.bytes;
    std::array<unsigned char, sizeof(value)> objectBefore;
    std::memcpy(objectBefore.data(), &value, sizeof(value));
    int result;
    switch (op) {
    case 0:
      result = value.read(buffer.data(), length);
      break;
    case 1:
      result = value.write(buffer.data(), length);
      break;
    case 2:
      result = value.readMsg(message);
      break;
    case 3:
      result = value.writeMsg(message);
      break;
    default:
      return 4;
    }
    bool untouched =
        before == buffer && oldMessage == message.bytes &&
        std::memcmp(objectBefore.data(), &value, sizeof(value)) == 0;
    if (result != static_cast<int>(expected) || untouched != bool(unchanged))
      return 5;
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 6;
  std::cout << "SharedMemoryComm portable replay: " << cases << " cases\n";
}
