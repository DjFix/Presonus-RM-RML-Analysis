#include "core/portable/coreparams.h"
#include "presonus/DAWChannel.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
using Core::Portable::ParamInfo;
class Probe : public Presonus::DAWChannel {
public:
  void add(const ParamInfo &info) { addParameters(&info, 1, false); }
};
int main() {
  static const ParamInfo type = PARAM_STRING(0, "type", 0);
  static const ParamInfo id = PARAM_STRING(22, "id", 0);
  Probe first, second, absent;
  for (auto *channel : {&first, &second}) {
    channel->add(type);
    channel->add(id);
    channel->getParameterByTag(22)->fromString("separate-id", false);
    channel->init(false);
  }
  absent.init(false);
  const char *idBuffer = first.getID();
  assert(std::string(idBuffer) == "separate-id");
  assert(absent.getType() == nullptr);
  std::cout << "null\n";
  const char *shared = nullptr;
  const std::string values[] = {"",
                                "input",
                                std::string(31, 'A'),
                                std::string(32, 'B'),
                                std::string(80, 'C'),
                                "x"};
  int i = 0;
  for (const auto &value : values) {
    Probe &channel = (i++ == 2 || i == 4 || i == 6) ? second : first;
    channel.getParameterByTag(0)->fromString(value.c_str(), false);
    const char *result = channel.getType();
    if (shared)
      assert(result == shared);
    shared = result;
    assert(result != idBuffer);
    assert(std::memchr(result, '\0', 32) != nullptr);
    assert(std::strlen(result) <= 31);
    assert(std::string(result) == value.substr(0, 31));
    assert(std::string(idBuffer) == "separate-id");
    std::cout << result << '\n';
  }
  assert(absent.getType() == nullptr && std::string(shared) == "x");
  std::cout << "null\n";
}
