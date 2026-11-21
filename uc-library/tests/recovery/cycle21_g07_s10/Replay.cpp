#include "core/public/corememstream.h"
#include "presonus/MixerSceneLoader.hpp"
#include <cstdio>
#include <stdexcept>
#include <string>

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string hex = argv[2];
  if (hex.size() % 2 != 0)
    return 2;
  auto *stream = new Core::IO::MemoryStream;
  MixerSceneLoader loader(stream, std::string(argv[1]) == "1");
  for (std::size_t i = 0; i < hex.size(); i += 2) {
    const auto byte =
        static_cast<unsigned char>(std::stoul(hex.substr(i, 2), nullptr, 16));
    if (stream->writeBytes(&byte, 1) != 1)
      return 3;
  }
  Core::Portable::Attributes attrs(
      Core::Portable::AttributeAllocator::getDefault());
  if (loader.load(attrs))
    std::printf("1 %s %lld\n", attrs.getString("name"), attrs.getInt("number"));
  else
    std::puts("0");
}
