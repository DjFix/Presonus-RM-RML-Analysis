#include "presonus/mixer/MixerComponentBase.hpp"
#include <iostream>
int main() {
  Core::Portable::Component graph("test");
  for (int state : {0, 5, 9}) {
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.childLookupParameters = &graph;
    mixer.sceneRecallBlocksTag14 = state != 0;
    mixer.setDanteStaticRoutes();
    if (mixer.childLookupParameters != &graph ||
        mixer.sceneRecallBlocksTag14 != (state != 0))
      return 1;
    std::cout << "unchanged" << '\n';
  }
}
