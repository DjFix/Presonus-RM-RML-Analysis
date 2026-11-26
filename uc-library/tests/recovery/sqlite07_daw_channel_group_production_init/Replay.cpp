#include "presonus/DAWChannel.hpp"
#include "presonus/DAWChannelGroup.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>
using Core::Portable::Component;
using Core::Portable::ParamInfo;
namespace {
static const ParamInfo used =
    PARAM_FLOAT(0, "used", -20, 20, 0, 0, nullptr, nullptr, 0, 0);
static const ParamInfo infos[] = {
    PARAM_FLOAT(0, "type", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(5, "five", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(6, "six", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(8, "eight", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(9, "nine", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(18, "eighteen", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(21, "twentyone", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(22, "id", 0, 1, 0, 0, nullptr, nullptr, 0, 0),
    PARAM_FLOAT(23, "twentythree", 0, 1, 0, 0, nullptr, nullptr, 0, 0)};
class InspectParameter : public Core::Portable::Parameter {
public:
  static bool feedback(const Parameter &parameter) {
    return (parameter.*&InspectParameter::flags & kFeedback) != 0;
  }
};
class Group : public Presonus::DAWChannelGroup {
public:
  bool feedback() const {
    return InspectParameter::feedback(*cachedParameter_);
  }
};
class Foreign : public Component {
public:
  Foreign(Group &g, int i) : group(g), index(i) {}
  void *castTo(int type) override {
    if (type == 0x44617743) {
      assert(group.feedback());
      std::cout << "cast " << index << '\n';
    }
    return Component::castTo(type);
  }
  Group &group;
  int index;
};
class Channel : public Presonus::DAWChannel {
public:
  Channel(Group &g, int i, bool flag) : group(g), index(i), flag(flag) {
    addParameters(infos, 9, false);
  }
  void *castTo(int type) override {
    if (type == 0x44617743) {
      assert(group.feedback());
      std::cout << "cast " << index << "\ninit " << index << ' ' << flag
                << '\n';
    }
    return DAWChannel::castTo(type);
  }
  Group &group;
  int index;
  bool flag;
};
} // namespace
int main(int argc, char **argv) {
  assert(argc == 3);
  bool flag = std::atoi(argv[1]);
  int count = std::atoi(argv[2]);
  Group group;
  group.addParameters(&used, 1, false);
  std::vector<Channel *> channels;
  for (int i = 0; i < count; ++i) {
    if (i % 2) {
      auto *channel = new Channel(group, i, flag);
      channels.push_back(channel);
      group.addChild(channel);
    } else
      group.addChild(new Foreign(group, i));
  }
  std::cout << "feedback 1\n";
  group.init(flag);
  assert(group.feedback());
  for (auto *channel : channels) {
    assert(channel->getType() != nullptr);
    assert(channel->countParameters() == (flag ? 7 : 12));
    std::cout << "channel " << channel->index << ' '
              << channel->countParameters() << '\n';
  }
}
