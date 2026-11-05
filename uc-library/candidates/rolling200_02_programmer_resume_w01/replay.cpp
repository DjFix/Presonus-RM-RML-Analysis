#include "presonus/noaa/programmer.hpp"
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

// TEST ONLY boundary captures. These are not production providers or recovered
// implementations. Only the four approved production methods are under replay.
namespace {
int failAt, boundaryIndex, cancelAfter, chunks;
bool overwriteCount;
std::int64_t epochValue;
std::vector<std::string> events;
std::string hex(const unsigned char *data, std::size_t size) {
  static constexpr char digits[] = "0123456789abcdef";
  std::string result;
  for (std::size_t i = 0; i < size; ++i) {
    result += digits[data[i] >> 4];
    result += digits[data[i] & 15];
  }
  return result;
}
std::string hex(const char *text) {
  const std::string value(text);
  return hex(reinterpret_cast<const unsigned char *>(value.data()),
             value.size());
}
struct Services : presonus::noaa::ProgrammerReceiveServices {
  std::int64_t clockRawTicks() override { return 1234567890123LL; }
  std::int32_t readByte(std::int32_t, unsigned char *) override {
    std::abort();
  }
  void responseTimeout() override { std::abort(); }
  void responseReadError(std::int32_t) override { std::abort(); }
  void debugMessage(const char *text) override {
    events.push_back("D " + hex(text));
  }
} services;
int outcome() { return boundaryIndex++ == failAt ? 0 : 1; }
} // namespace
namespace presonus::noaa {
ProgrammerReceiveServices &posixProgrammerReceiveServices() { return services; }
void setProgrammerProgressEpochMilliseconds(std::int64_t value) {
  epochValue = value;
}
} // namespace presonus::noaa
namespace Presonus::NOAA {
TCardProgrammer::TCardProgrammer(UC::IFirmwareUpdateListener *,
                                 const unsigned char *image,
                                 unsigned int length)
    : transport_(nullptr) {
  state_.image = image;
  state_.length = length;
  receive_ = &services;
}
TCardProgrammer::~TCardProgrammer() = default;
std::int32_t TCardProgrammer::doCommand(unsigned char command) {
  int result = outcome();
  events.push_back("C " + std::to_string(command) + " " +
                   std::to_string(result));
  return result;
}
std::int32_t TCardProgrammer::waitAck(int timeout) {
  int result = outcome();
  events.push_back("A " + std::to_string(timeout) + " " +
                   std::to_string(result));
  if (overwriteCount) {
    state_.response.packetData()[0] = 0;
    events.push_back("O 0");
  }
  return result;
}
std::int32_t TCardProgrammer::writeChar(unsigned char value) {
  events.push_back("B " + std::to_string(value));
  return 1;
}
std::int32_t TCardProgrammer::sendAddress(unsigned int value) {
  events.push_back("S " + std::to_string(value));
  return 1;
}
std::int32_t TCardProgrammer::sendPacket(const unsigned char *data,
                                         int length) {
  events.push_back("T " + hex(data, static_cast<std::size_t>(length)));
  return 1;
}
void TCardProgrammer::printProgress(const char *message, bool emit) {
  events.push_back("G " + hex(message) + " " + std::to_string(emit ? 1 : 0));
  if (std::string(message).find("writing address") == 0 &&
      ++chunks == cancelAfter) {
    state_.byte24 = 1;
    events.push_back("X 1");
  }
}
} // namespace Presonus::NOAA
int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  const std::string method(argv[1]);
  unsigned int length = static_cast<unsigned int>(std::stoul(argv[2]));
  if (length > 512)
    return 2;
  failAt = std::stoi(argv[4]);
  cancelAfter = std::stoi(argv[5]);
  overwriteCount = std::stoi(argv[6]) != 0;
  std::vector<unsigned char> image(length);
  for (unsigned int i = 0; i < length; ++i)
    image[i] = static_cast<unsigned char>(i * 37 + 11);
  Presonus::NOAA::TCardProgrammer object(nullptr, image.data(), length);
  auto &state = presonus::noaa::ProgrammerAccess::mutableState(object);
  state.byte24 = static_cast<unsigned char>(std::stoi(argv[3]));
  int result = 0;
  if (method == "writeImage")
    result = object.writeImage();
  else if (method == "update")
    result = object.update();
  else if (method == "eraseAll")
    result = object.eraseAll();
  else if (method == "unprotect")
    result = object.unprotect();
  else
    return 2;
  std::cout << "R " << result << '\n';
  std::cout << "P " << hex(state.response.packetData(), 257) << '\n';
  std::cout << "F " << static_cast<int>(state.byte24) << '\n';
  for (const auto &event : events)
    std::cout << event << '\n';
  if (std::string(argv[7]) == "epoch")
    std::cout << "E " << epochValue << '\n';
}
