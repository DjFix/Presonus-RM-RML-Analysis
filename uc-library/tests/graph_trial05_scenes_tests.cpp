#include "presonus/StormMixSceneComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
static std::vector<std::string> trace;
static std::uint32_t bits(float f) {
  std::uint32_t u;
  std::memcpy(&u, &f, 4);
  return u;
}
static float number(std::uint32_t u) {
  float f;
  std::memcpy(&f, &u, 4);
  return f;
}
struct P : NumericParam {
  float raw;
  P(const ParamInfo &i, float value) : NumericParam(i), raw(value) {}
  float getValue() const override {
    trace.push_back("g" + std::to_string(getTag()));
    return raw;
  }
  void setValue(float value, bool edit) override {
    raw = value;
    trace.push_back("s" + std::to_string(getTag()) + ":" +
                    std::to_string(bits(value)) + ":" + std::to_string(edit));
  }
};
struct R : presonus::scene_port::Recall {
  bool result;
  bool recall(unsigned int i) const override {
    trace.push_back("r" + std::to_string(i));
    return result;
  }
};
struct D : presonus::scene_port::StoreDelegate {
  void enter(Presonus::StormMixSceneComponent &) override {
    trace.push_back("enter");
  }
  void leave(Presonus::StormMixSceneComponent &) override {
    trace.push_back("leave");
  }
};
struct T : presonus::scene_port::Timer {
  unsigned int id;
  bool run, longer;
  bool executing() const override {
    trace.push_back("e" + std::to_string(id));
    return run;
  }
  bool longEnough() const override {
    trace.push_back("l" + std::to_string(id));
    return longer;
  }
  void end() override {
    trace.push_back("end" + std::to_string(id));
    run = false;
  }
};
struct Child : Component {
  void onIdle() override { trace.push_back("idle"); }
};
struct Scene : Presonus::StormMixSceneComponent {
  using StormMixSceneComponent::StormMixSceneComponent;
  void add(Parameter *p) { paramList.add(p); }
};
static int providerSmoke() {
  R recall;
  recall.result = true;
  Scene scene(recall);
  Presonus::DelayTimer elapsed(-0.001f), waiting(1.f), inactive(1.f);
  using Access = presonus::timing::DelayTimerAccess;
  Access::set(elapsed, {0, -1, 0, 0, true});
  Access::set(waiting, {0, INT64_MAX, 0, 0, true});
  Presonus::DelayTimer *timers[] = {nullptr, &elapsed, &waiting, &inactive};
  scene.configureTimers(timers, 4);
  trace.clear();
  scene.onIdle();
  if (elapsed.isExecuting() || !waiting.isExecuting() ||
      inactive.isExecuting() || scene.recalledIndex() != 1 ||
      trace != std::vector<std::string>{"r1"} ||
      Access::get(elapsed).elapsed < -1)
    return 10;
  std::cout << "Real DelayTimer scene provider smoke passed\n";
  return 0;
}
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider-smoke")
    return providerSmoke();
  if (argc != 11)
    return 2;
  unsigned v[10];
  for (int i = 0; i < 10; ++i)
    v[i] = std::stoul(argv[i + 1]);
  R recall;
  recall.result = v[4];
  Scene scene(recall);
  D delegate;
  if (v[6])
    scene.configureStoreDelegate(&delegate);
  std::array<ParamInfo, 8> infos{};
  std::array<P *, 8> params{};
  for (unsigned i = 0; i < 8; ++i)
    if (v[2] & (1U << i)) {
      auto &p = infos[i];
      p.type = ParamInfo::kFloat;
      p.tag = i;
      p.minValue = -100;
      p.maxValue = 100;
      params[i] = new P(p, i ? 0.25f : number(v[1]));
      scene.add(params[i]);
    }
  std::array<T, 4> timer;
  presonus::scene_port::Timer *timers[4];
  for (unsigned i = 0; i < 4; ++i) {
    timer[i].id = i;
    timer[i].run = v[8] & (1U << i);
    timer[i].longer = v[9] & (1U << i);
    timers[i] = (v[7] & (1U << i)) ? &timer[i] : nullptr;
  }
  scene.configureFixtureTimers(timers, 4);
  scene.addChild(new Child);
  trace.clear();
  int result = -1;
  switch (v[0]) {
  case 1:
    result = scene.isStoreOn();
    break;
  case 2:
    scene.enterStoreState(v[3]);
    break;
  case 3:
    scene.setAllMixButtons(v[3]);
    break;
  case 4:
    scene.doRecall(v[5]);
    break;
  case 5:
    scene.onIdle();
    break;
  default:
    return 3;
  }
  std::cout << result << " " << scene.recalledIndex();
  for (auto *p : params)
    std::cout << " " << (p ? std::to_string(bits(p->raw)) : "-");
  std::cout << " |";
  for (auto &t : trace)
    std::cout << " " << t;
  std::cout << "\n";
}
