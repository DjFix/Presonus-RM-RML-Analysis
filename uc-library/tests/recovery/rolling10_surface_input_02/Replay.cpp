#include "core/portable/coreparams.h"
#include "presonus/surface/SurfaceInputComponent.hpp"
#include <iostream>
using namespace Core::Portable;
BEGIN_PARAMINFO(parameters)
PARAM_FLOAT_(301, "pot", -100, 100, 0, .001, "", "", 0, 0, "Pot", nullptr),
    PARAM_FLOAT_(300, "level", -100, 100, 0, .001, "", "", 0, 0, "Level",
                 nullptr),
    PARAM_FLOAT_(302, "other", -100, 100, 0, .001, "", "", 0, 0, "Other",
                 nullptr),
    END_PARAMINFO int main() {
  for (int count = 0; count <= 3; ++count) {
    Presonus::Surface::SurfaceInputComponent owner;
    owner.addParameters(parameters, count);
    const auto &view = owner;
    auto *before = view.getParameterByTag(301);
    for (int repeat = 0; repeat < 8; ++repeat) {
      auto *actual = view.getPotValue();
      if (actual != before)
        return 2;
      if (actual && actual->getTag() != 301)
        return 3;
    }
    std::cout << count << ' ' << (before != nullptr) << '\n';
  }
}
