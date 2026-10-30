// STAGED ONLY: no fixture generation, compilation or execution authorized yet.
#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <time.h>
#include <unistd.h>
#include <vector>
namespace fixture {
std::vector<unsigned char> input;
std::vector<std::string> writes;
std::size_t cursor;
std::uint64_t milliseconds;
std::array<int, 16> writeResults;
unsigned resultCount, resultCursor;
unsigned nibble(char c) { return c <= '9' ? c - '0' : c - 'a' + 10; }
std::string decode(const std::string &hex) {
  if (hex == "-")
    return {};
  assert(hex.size() % 2 == 0);
  std::string value;
  for (unsigned i = 0; i < hex.size(); i += 2)
    value += static_cast<char>((nibble(hex[i]) << 4) | nibble(hex[i + 1]));
  return value;
}
} // namespace fixture
extern "C" ssize_t __wrap_read(int descriptor, void *data, size_t size) {
  assert(descriptor == 73 && size == 1);
  if (fixture::cursor < fixture::input.size()) {
    *static_cast<unsigned char *>(data) = fixture::input[fixture::cursor++];
    return 1;
  }
  fixture::milliseconds += 500;
  return 0;
}
extern "C" ssize_t __wrap___read_chk(int fd, void *data, size_t size,
                                     size_t capacity) {
  assert(capacity >= size && size == 1);
  return __wrap_read(fd, data, size);
}
extern "C" ssize_t __wrap_write(int descriptor, const void *data, size_t size) {
  assert(descriptor == 73 && size <= 128);
  fixture::writes.emplace_back(static_cast<const char *>(data), size);
  if (fixture::resultCursor < fixture::resultCount)
    return fixture::writeResults[fixture::resultCursor++];
  return size;
}
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *value) {
  assert(clock == CLOCK_MONOTONIC);
  value->tv_sec = fixture::milliseconds / 1000;
  value->tv_nsec = fixture::milliseconds % 1000 * 1000000;
  return 0;
}
int main() {
  using namespace presonus::lpc;
  unsigned kind, expectedReturn, expectedWriteCount;
  int timeout;
  std::string commandHex, inputHex;
  unsigned count = 0;
  while (std::cin >> kind >> timeout >> commandHex >> inputHex >>
         fixture::resultCount) {
    assert(kind < 3 && fixture::resultCount <= fixture::writeResults.size());
    for (unsigned i = 0; i < fixture::resultCount; ++i)
      std::cin >> fixture::writeResults[i];
    std::array<std::uint32_t, 6> expected;
    std::cin >> expectedReturn >> expectedWriteCount;
    for (auto &word : expected)
      std::cin >> word;
    std::vector<std::string> expectedWrites;
    for (unsigned i = 0; i < expectedWriteCount; ++i) {
      std::string hex;
      std::cin >> hex;
      expectedWrites.push_back(fixture::decode(hex));
    }
    const auto command = fixture::decode(commandHex);
    assert(command.find('\0') == std::string::npos);
    const auto bytes = fixture::decode(inputHex);
    fixture::input.assign(bytes.begin(), bytes.end());
    fixture::writes.clear();
    fixture::cursor = 0;
    fixture::milliseconds = 0;
    fixture::resultCursor = 0;
    InputState input;
    input.descriptor = 73;
    input.response.fill(static_cast<char>(0xa5));
    ImageGeometryState image;
    image.raw18 = 0xa5a5a5a5u;
    DeviceIdentityState identity;
    identity.raw1c_to28.fill(0xa5a5a5a5u);
    identity.raw2c = 0xa5a5a5a5u;
    Presonus::LPCProgrammer programmer(IdentityOnly{}, input, image, identity);
    const int result = kind == 0 ? programmer.writeString(command.c_str())
                       : kind == 1
                           ? programmer.waitValue(command.c_str(), timeout)
                           : programmer.readInfo();
    assert(static_cast<unsigned>(result) == expectedReturn);
    assert(fixture::writes == expectedWrites);
    const auto &actual = DeviceIdentityAccess::state(programmer);
    assert(ImageGeometryAccess::state(programmer).raw18 == expected[0]);
    assert(actual.raw2c == expected[1]);
    for (unsigned i = 0; i < 4; ++i)
      assert(actual.raw1c_to28[i] == expected[i + 2]);
    ++count;
  }
  assert(count != 0);
  std::cout << "PASS staged_command_info_cases=" << count << '\n';
}
