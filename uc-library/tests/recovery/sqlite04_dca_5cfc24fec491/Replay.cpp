#include "presonus/mixer/DCALevelHandler.hpp"
#include "presonus/mixer/FilterGroupComponent.hpp"

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using namespace Core::Portable;
using Presonus::Mixer::DCALevelHandler;
using Presonus::Mixer::FilterGroupComponent;

namespace {
using MastersMember = Core::Vector<Parameter *> DCALevelHandler::*;
struct MastersTag {
  friend MastersMember getMasters(MastersTag);
};
template <MastersMember Member> struct ObserveMasters {
  friend MastersMember getMasters(MastersTag) { return Member; }
};
// Explicit instantiation gives the test access to the actual provider vector.
template struct ObserveMasters<&DCALevelHandler::masters_>;
} // namespace

int main(int argc, char **argv) {
  if (argc < 5)
    return EXIT_FAILURE;
  const std::string mode(argv[1]);
  const int count = std::stoi(argv[2]);
  const int selected = std::stoi(argv[3]);
  const int tag = std::stoi(argv[4]);
  const ParamInfo info{ParamInfo::kFloat, tag, "gain", -10000.f, 10000.f};
  const ParamInfo otherInfo{ParamInfo::kFloat, tag ^ 1, "other", -10000.f,
                            10000.f};
  NumericParam level(info);
  NumericParam trim(info);
  FilterGroupComponent missing(FilterGroupComponent::SourcePortConstruction{});
  missing.addParameters(&otherInfo, 1);
  const auto groupNumber = selected < 0 ? nullptr : &info;
  if (mode == "provider") {
    FilterGroupComponent group(FilterGroupComponent::SourcePortConstruction{});
    group.addParameters(groupNumber ? groupNumber : &otherInfo, 1);
    Core::Vector<Parameter *> vector(0, 5);
    const bool resized = vector.resize(count);
    std::cout << (group.getParameterByTag(tag) ? selected : -1) << ' '
              << resized << ' ' << vector.getCapacity() << '\n';
    return EXIT_SUCCESS;
  }

  std::vector<std::unique_ptr<FilterGroupComponent>> groups;
  for (int i = 0; i <= count; ++i) {
    auto group = std::make_unique<FilterGroupComponent>(
        FilterGroupComponent::SourcePortConstruction{});
    group->addParameters(&info, 1);
    groups.push_back(std::move(group));
  }
  DCALevelHandler handler(&level, &trim, tag);
  for (int i = 0; i < count; ++i)
    handler.addDCAMaster(groups[i].get());

  const auto &masters = handler.*getMasters(MastersTag{});
  auto *target = selected < 0 ? &missing : groups.at(selected).get();
  if (mode == "add")
    handler.addDCAMaster(target);
  else if (mode == "remove")
    handler.removeDCAMaster(target);
  else
    return EXIT_FAILURE;
  std::cout << "roster";
  for (const auto *parameter : masters) {
    for (size_t i = 0; i < groups.size(); ++i)
      if (groups[i]->getParameterByTag(tag) == parameter)
        std::cout << ' ' << i;
  }
  std::cout << '\n' << "capacity " << masters.getCapacity() << '\n';
  if (mode == "remove" && masters.count() != count)
    std::cout << "tail-cleared "
              << (masters.getItems()[count - 1] == masters.getError()) << '\n';
}
