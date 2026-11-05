#include "presonus/SLChannel.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  if (!fixture)
    return 3;
  using Method =
      Core::Portable::Parameter *(Presonus::SLChannelBase::*)() const;
  const std::array<Method, 4> methods = {
      &Presonus::SLChannelBase::getLinkParameter,
      &Presonus::SLChannelBase::getColorParameter,
      &Presonus::SLChannelBase::getLinkMasterParameter,
      &Presonus::SLChannelBase::getLinkedSelectionParameter};
  unsigned method, seed, expected, outsideWrites, calls;
  std::size_t count = 0;
  while (fixture >> method >> seed >> expected >> outsideWrites >> calls) {
    if (method >= methods.size() || outsideWrites || calls)
      return 4;
    const std::string name(seed % 37, static_cast<char>('a' + seed % 26));
    Presonus::SLChannelBase base(name.c_str());
    Presonus::SLChannel derived(name.c_str(), nullptr);
    const Presonus::SLChannelBase *object = seed % 2 ? &derived : &base;
    const std::size_t size = seed % 2 ? sizeof(derived) : sizeof(base);
    std::vector<unsigned char> before(size);
    std::memcpy(before.data(), object, size);
    const auto actual =
        reinterpret_cast<std::uintptr_t>((object->*methods[method])());
    if (actual != expected || std::memcmp(before.data(), object, size))
      return 5;
    ++count;
  }
  if (!fixture.eof() || !count)
    return 6;
  std::cout << "Passed " << count
            << " native fixture rows; valid base/derived instances, nullable "
               "returns, unchanged object representations\n";
}
