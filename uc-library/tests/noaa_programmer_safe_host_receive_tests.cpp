#include "presonus/noaa/programmer.hpp"
#include <cassert>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <unistd.h>
#include <utility>
#include <vector>
using namespace presonus::noaa;
struct NoDeviceTransport : ProgrammerTransport {
  std::int32_t write(std::int32_t, const unsigned char *,
                     std::uint32_t) override {
    std::abort();
  }
  std::int32_t close(std::int32_t) override { return -1; }
};
struct Script : ProgrammerReceiveServices {
  std::int64_t start, step;
  unsigned clocks = 0, reads = 0;
  std::vector<std::pair<int, unsigned>> input;
  std::vector<std::string> events;
  std::int64_t clockRawTicks() override {
    auto value = start + step * clocks++;
    events.push_back("C:" + std::to_string(value));
    return value;
  }
  std::int32_t readByte(std::int32_t fd, unsigned char *byte) override {
    auto value = input[std::min<std::size_t>(reads++, input.size() - 1)];
    if (value.first > 0)
      *byte = static_cast<unsigned char>(value.second);
    events.push_back("R:" + std::to_string(fd) + ":" +
                     std::to_string(value.first) + ":" +
                     (value.first > 0 ? std::to_string(value.second) : "-"));
    return value.first;
  }
  void debugMessage(const char *) override { std::abort(); }
  void responseTimeout() override { events.push_back("T"); }
  void responseReadError(std::int32_t value) override {
    events.push_back("E:" + std::to_string(value));
  }
};
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream file(argv[1]);
  assert(file);
  std::string line;
  unsigned cases = 0;
  while (std::getline(file, line)) {
    std::istringstream in(line);
    int timeout, fd;
    unsigned n;
    Script script;
    in >> timeout >> fd >> script.start >> script.step >> n;
    for (unsigned i = 0; i < n; ++i) {
      int result;
      unsigned byte;
      in >> result >> byte;
      script.input.emplace_back(result, byte);
    }
    std::uint32_t expected;
    std::string expectedResponse;
    in >> expected >> expectedResponse;
    unsigned eventCount;
    in >> eventCount;
    std::vector<std::string> events;
    for (unsigned i = 0; i < eventCount; ++i) {
      std::string e;
      in >> e;
      events.push_back(e);
    }
    assert(in);
    NoDeviceTransport transport;
    Presonus::NOAA::TCardProgrammer object(nullptr, nullptr, 0);
    ProgrammerAccess::bind(object, transport, fd);
    ProgrammerAccess::bindReceive(object, script);
    auto &state = ProgrammerAccess::mutableState(object);
    state.response.fill(0xa5);
    auto result = object.waitResponse(timeout);
    assert(static_cast<std::uint32_t>(result) == expected);
    assert(script.events == events);
    std::ostringstream response;
    response << std::hex << std::setfill('0');
    for (auto byte : state.response)
      response << std::setw(2) << static_cast<unsigned>(byte);
    assert(response.str() == expectedResponse);
    ++cases;
  }
  assert(cases == 313);
  // Real production CCL clock/debug and POSIX read, using only a kernel pipe.
  int descriptors[2];
  assert(::pipe(descriptors) == 0);
  const unsigned char bytes[] = {0x55, 0x79};
  assert(::write(descriptors[1], bytes, 2) == 2);
  {
    NoDeviceTransport transport;
    Presonus::NOAA::TCardProgrammer object(nullptr, nullptr, 0);
    ProgrammerAccess::bind(object, transport, descriptors[0]);
    auto &state = ProgrammerAccess::mutableState(object);
    state.response.fill(0xa5);
    assert(object.waitResponse(2000) == 2);
    assert(state.response[0] == 0x55 && state.response[1] == 0x79 &&
           state.response[2] == 0 && state.response[128] == 0xa5);
    assert(object.waitResponse(0) == -1);
    ProgrammerAccess::bind(object, transport, -1);
    assert(object.waitResponse(2000) == -1);
  }
  assert(::close(descriptors[0]) == 0 && ::close(descriptors[1]) == 0);
  std::printf(
      "{\"passed\":true,\"cases\":%u,\"hardware_operations\":0,\"actual_posix_"
      "pipe_replay\":true,\"actual_ccl_clock_debug_provider\":true}\n",
      cases);
}
