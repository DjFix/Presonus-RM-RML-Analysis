#include "presonus/MappablePageComponent.hpp"
#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int tag = std::atoi(argv[1]);
  const int count = std::atoi(argv[2]);
  static const ParamInfo seed[] = {
      PARAM_TOGGLE(10, "a", 0, nullptr, 0),
      PARAM_TOGGLE(11, "b", 0, nullptr, 0),
      PARAM_TOGGLE(12, "c", 0, nullptr, 0),
      PARAM_TOGGLE(13, "d", 0, nullptr, 0),
  };
  NumericParam original(seed[0]);
  Presonus::MappablePageComponent page("mapping");
  page.addParameters(seed, count);
  page.addAlias(tag, "level_alias");
  auto *alias = AliasParam::cast(page.findParameter("level_alias"));
  if (!alias)
    return 3;
  const bool tagIndex = page.getParameterByTag(alias->getTag()) == alias;
  const bool connects = page.connectParameter("level_alias", &original) &&
                        alias->getOriginal() == &original;
  page.disconnectMappables();
  std::cout << alias->getTag() << ' ' << page.countParameters() << ' '
            << tagIndex << ' ' << connects << ' '
            << (alias->getOriginal() == nullptr) << '\n';
}
