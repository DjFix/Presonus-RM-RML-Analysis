#include "presonus/MuteGroupBase.hpp"
#include <iostream>
#include <memory>
#include <vector>
using namespace Core::Portable;
struct Boundary : NumericParam {
  static const ParamInfo info;
  float v = 0, m = 0;
  Boundary(float value, float maximum)
      : NumericParam(info), v(value), m(maximum) {}
  float getValue() const override { return v; }
  float getMax() const override { return m; }
  void setValue(float value, bool) override { v = value; }
  void setMax(float value) override { m = value; }
  void resetValue(bool) override { v = 0; }
};
const ParamInfo Boundary::info = {};
int main() {
  int method, n;
  float a, s, t, m;
  while (std::cin >> method >> a >> s >> t >> m >> n) {
    Boundary active(a, m), status(s, m), alternate(t, m);
    presonus::mute_group_port::State state;
    state.active = &active;
    state.status = &status;
    state.alternateStatus = &alternate;
    std::vector<std::unique_ptr<Boundary>> members;
    for (int i = 0; i < n; ++i) {
      float value;
      std::cin >> value;
      members.emplace_back(new Boundary(value, m));
      state.members.add(members.back().get());
    }
    Presonus::MuteGroupBase group(state);
    int result = -1;
    switch (method) {
    case 0:
      group.updateActive();
      break;
    case 1:
      group.updateStatus();
      break;
    case 2:
      result = group.groupDirty();
      break;
    case 3:
      result = group.validStatus(&status);
      break;
    case 4:
      group.deactivate();
      break;
    }
    std::cout << result << ' ' << active.v << ' ' << status.v << ' '
              << alternate.v << ' ' << status.m << ' ' << state.members.count()
              << '\n';
  }
}
