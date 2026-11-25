#include "presonus/application/SurfaceApplication.hpp"

#include <cstring>
#include <iostream>
#include <type_traits>

int main() {
  using Core::Portable::FileName;
  using Presonus::Surface::SurfaceApplication;
  static_assert(std::is_same_v<decltype(&SurfaceApplication::getSkinDirectory),
                               FileName (*)()>);
  SurfaceApplication first{};
  SurfaceApplication second{};
  using presonus::application::SurfaceSerialStateAccess;
  SurfaceSerialStateAccess::seed(first, 0x12345);
  SurfaceSerialStateAccess::seed(second, 0x6789ab);
  auto one = first.getSkinDirectory();
  auto two = second.getSkinDirectory();
  std::cout << one.str() << '\n' << two.str() << '\n';
  one.getBuffer()[1] = 'X';
  const auto three = first.getSkinDirectory();
  std::cout << one.str() << '\n'
            << two.str() << '\n'
            << three.str() << '\n'
            << (one.getBuffer() != two.getBuffer()) << ' '
            << (one.getBuffer() != three.str()) << ' '
            << (two.getBuffer() != three.str()) << ' '
            << (SurfaceSerialStateAccess::value(first) == 0x12345) << ' '
            << (SurfaceSerialStateAccess::value(second) == 0x6789ab) << '\n';
}
