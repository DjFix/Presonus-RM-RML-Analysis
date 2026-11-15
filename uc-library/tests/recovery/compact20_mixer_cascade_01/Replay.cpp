#include "presonus/mixer/CascadeLinkHandler.hpp"
#include <cstdint>
#include <cstdlib>
#include <iostream>
int main(int argc, char **argv) {
  if (argc < 5)
    return 2;
  using Handler = Presonus::Mixer::CascadeLinkHandler;
  Core::Vector<Handler::ParamLink *> primary, pending;
  const int repeats = std::atoi(argv[1]);
  const int id = std::atoi(argv[2]);
  const int present = std::atoi(argv[3]);
  const int n = std::atoi(argv[4]);
  if (argc < 5 + n)
    return 2;
  for (int i = 0; i < n; ++i)
    primary.add(reinterpret_cast<Handler::ParamLink *>(
        std::strtoull(argv[5 + i], nullptr, 10)));
  for (int i = 5 + n; i < argc; ++i)
    pending.add(reinterpret_cast<Handler::ParamLink *>(
        std::strtoull(argv[i], nullptr, 10)));
  Handler handler(primary, pending, present ? &id : nullptr);
  for (int i = 0; i < repeats; ++i)
    handler.connectDevice();
  std::cout << "RESULT [";
  for (int i = 0; i < pending.count(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << reinterpret_cast<std::uintptr_t>(pending.at(i));
  }
  std::cout << "]\n";
}
