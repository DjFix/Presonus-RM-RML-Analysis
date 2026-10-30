#include "core/public/corememstream.h"
#include "presonus/application/SimpleReader.hpp"
#include "presonus/application/SimpleReaderEnvironment.hpp"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <type_traits>

struct ReaderOnlyEnvironment final
    : presonus::startup::SimpleReaderEnvironmentBindings {
  [[noreturn]] static int unavailable() {
    throw std::logic_error("concrete application remains unrecovered");
  }
  void *construct(presonus::startup::Kind, int) override { unavailable(); }
  int init(void *) override { return unavailable(); }
  int run(void *) override { return unavailable(); }
  int idle(void *) override { return unavailable(); }
  int shutdown(void *) override { return unavailable(); }
  int runTests(void *, int, int, char **) override { return unavailable(); }
  void release(void *, presonus::startup::Role) override { unavailable(); }
};

static_assert(
    std::is_abstract_v<presonus::startup::SimpleReaderEnvironmentBindings>);
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::string data = "OTHER=first\nDEVICE_NAME=storm\n";
  Core::IO::MemoryStream stream(data.data(),
                                static_cast<Core::uint32>(data.size()));
  Presonus::SimpleReader reader(stream);
  Core::CStringBuffer<64> out;
  const Core::ConstString key("DEVICE_NAME");
  if (!reader.getValueForKey(out, key) || out.length() != 0)
    return 3;
  if (!reader.getValueForKey(out, key) || out.length() != 0)
    return 4;
  if (!reader.getValueForKey(out, key) || !(out == "storm"))
    return 7;
  out = "kept";
  if (!reader.findValueForKey(out, key) || !(out == "kept"))
    return 5;
  std::ofstream file(argv[1]);
  file << "DEVICE_NAME=rogue\n";
  file.close();
  out = "default";
  ReaderOnlyEnvironment environment;
  environment.readDeviceName(out, key, Core::ConstString(argv[1]));
  if (!(out == "rogue"))
    return 6;
  std::cout << "actual CCL memory/file reader binding smoke passed; ARM "
               "differential still pending\n";
}
