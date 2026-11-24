#include "presonus/application/SurfaceApplication.hpp"
#include <iostream>

int main() {
  using presonus::application::SurfaceSerialStateAccess;
  Presonus::Surface::SurfaceApplication app;
  const auto &receiver = app;
  for (unsigned seed = 0; seed < 4; ++seed) {
    const unsigned serial = 0x12345678 + seed;
    SurfaceSerialStateAccess::seed(app, serial);
    for (int repeat : {0, 1}) {
      const auto word = receiver.isNetworkClientReady();
      std::cout << seed << ' ' << repeat << ' ' << word << ' '
                << (SurfaceSerialStateAccess::value(app) != serial) << '\n';
    }
  }
}
