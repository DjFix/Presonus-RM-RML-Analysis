#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
namespace {
std::vector<std::string> trace;
}
extern "C" char *__real_strstr(const char *, const char *);
extern "C" int __real_strcmp(const char *, const char *);
extern "C" char *__wrap_strstr(const char *name, const char *token) {
  trace.push_back(std::string("strstr:") + token);
  return __real_strstr(name, token);
}
extern "C" int __wrap_strcmp(const char *name, const char *token) {
  trace.push_back(std::string("strcmp:") + token);
  return __real_strcmp(name, token);
}
int main() {
  Presonus::Surface::SurfaceRootComponent root;
  std::string line;
  while (std::getline(std::cin, line)) {
    trace.clear();
    const char *name = line == "NULL" ? nullptr : line.c_str();
    const bool mapping = root.isMappableControl(name);
    const bool transport = root.isTransportControl(name);
    std::cout << mapping << ' ' << transport;
    for (const auto &call : trace)
      std::cout << ' ' << call;
    std::cout << '\n';
  }
}
