#include "presonus/DAWChannel.hpp"
#include "presonus/DAWDeviceFolder.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <string_view>

using Presonus::DAWChannel;
using Presonus::DAWDeviceFolder;
using namespace Core::Portable;

namespace {

void require(bool valid) {
  if (!valid)
    std::abort();
}

struct FixtureChannel : DAWChannel {
  void bindSelected(Parameter *p) { cachedParameters_[selectedCache] = p; }
  void bindID(Parameter *p) { cachedParameters_[idCache] = p; }
};

void replayFolder(std::string_view method, std::string_view variation) {
  using Getter = DAWDeviceFolder *(DAWChannel::*)() const;
  struct Mapping {
    std::string_view method;
    const char *name;
    Getter getter;
  };
  constexpr Mapping mappings[] = {
      {"getCueMixes", "cuemix", &DAWChannel::getCueMixes},
      {"getInserts", "inserts", &DAWChannel::getInserts},
      {"getPosts", "posts", &DAWChannel::getPosts},
      {"getSends", "sends", &DAWChannel::getSends},
  };
  for (const auto &mapping : mappings) {
    if (mapping.method != method)
      continue;
    DAWChannel channel;
    DAWDeviceFolder *wanted = nullptr;
    if (variation == "foreign") {
      channel.addChild(new Component(mapping.name));
    } else if (variation == "wrong-name" || variation == "match") {
      auto *folder = new DAWDeviceFolder;
      if (variation == "match") {
        folder->setName(mapping.name);
        wanted = folder;
      } else {
        const std::string other = std::string(mapping.name) + "Other";
        folder->setName(other.c_str());
      }
      channel.addChild(folder);
    } else {
      require(variation == "missing");
    }

    auto *found = (channel.*mapping.getter)();
    require(found == wanted);
    std::puts(found ? "identity" : "null");
    return;
  }
  std::abort();
}

void replaySelected(std::string_view input) {
  FixtureChannel channel;
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.minValue = -10;
  info.maxValue = 10;
  info.defaultValue = 1;
  NumericParam parameter(info);
  if (input != "missing") {
    const float value = std::strtof(input.data(), nullptr);
    parameter.setValue(value, false);
    require(parameter.getValue() == value);
    require(std::signbit(parameter.getValue()) == std::signbit(value));
    channel.bindSelected(&parameter);
  }
  std::printf("%d\n", channel.isSelected() ? 1 : 0);
}

void replayID(std::string_view presence, const char *input) {
  ParamInfo info{};
  info.type = ParamInfo::kString;
  StringParam initial(info);
  StringParam parameter(info);
  FixtureChannel first;
  FixtureChannel second;
  initial.fromString("previous", false);
  first.bindID(&initial);
  const auto *shared = first.getID();
  require(shared && std::strcmp(shared, "previous") == 0);
  if (presence == "missing") {
    require(second.getID() == nullptr && std::strcmp(shared, "previous") == 0);
    std::puts("null");
    return;
  }
  require(presence == "present" && input);
  parameter.fromString(input, false);
  require(parameter.getText() == input);
  second.bindID(&parameter);
  const auto *result = second.getID();
  require(result == shared);
  require(std::strlen(result) <= 63);
  std::puts(result);
}

} // namespace

int main(int argc, char **argv) {
  require(argc == 3 || argc == 4);
  const std::string_view method = argv[1];
  if (method == "isSelected") {
    replaySelected(argv[2]);
  } else if (method == "getID") {
    replayID(argv[2], argc == 4 ? argv[3] : nullptr);
  } else {
    replayFolder(method, argv[2]);
  }
}
