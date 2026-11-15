#include "presonus/mixer/GlobalComponent.hpp"
#include <array>
#include <cassert>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
struct Destruction : ParamObserverBase {
  int count = 0;
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kDestroyed)
      ++count;
  }
};
struct Oracle : Component {
  int changes = 0;
  Oracle(const ParamInfo *infos) : Component("global") {
    paramList.setFeedbackNeeded(true);
    paramList.add(infos, 53, false);
  }
  void paramChanged(Parameter *, int) override { ++changes; }
};
struct Product : Presonus::Mixer::GlobalComponent {
  int changes = 0;
  using GlobalComponent::GlobalComponent;
  void paramChanged(Parameter *, int) override { ++changes; }
};
struct Metadata {
  std::array<ParamInfo, 53> infos{};
  std::array<std::array<std::string, 4>, 53> texts;
  std::array<std::vector<std::string>, 53> strings;
  std::array<std::vector<Core::CStringPtr>, 53> pointers;
  explicit Metadata(const char *path) {
    std::ifstream in(path);
    assert(in);
    for (int i = 0; i < 53; ++i) {
      auto &v = infos[i];
      std::string name;
      in >> v.type >> v.tag >> std::quoted(name) >> v.minValue >> v.maxValue >>
          v.midValue >> v.defaultValue >> v.deltaValue >> v.flags;
      assert(name.size() < sizeof(v.name));
      std::strcpy(v.name, name.c_str());
      for (auto &t : texts[i])
        in >> std::quoted(t);
      auto ptr = [&](int j) -> Core::CStringPtr {
        return texts[i][j] == "<null>" ? nullptr : texts[i][j].c_str();
      };
      v.unitName = ptr(0);
      v.curveName = ptr(1);
      v.title = ptr(2);
      v.shortTitle = ptr(3);
      int count;
      in >> count;
      assert(count >= 0 && count < 1000);
      strings[i].resize(count);
      for (auto &s : strings[i])
        in >> std::quoted(s);
      for (auto &s : strings[i])
        pointers[i].push_back(s.c_str());
      v.stringList = count ? pointers[i].data() : nullptr;
      assert(in);
    }
  }
};
void equal(Parameter *a, Parameter *b, const ParamInfo &info,
           Component *product, Component *oracle) {
  assert(a && b && a != b);
  assert(a->getController() == product && b->getController() == oracle);
  assert(a->getType() == info.type && a->getType() == b->getType());
  assert(a->getTag() == info.tag && a->getTag() == b->getTag());
  assert(std::strcmp(a->getName(), b->getName()) == 0);
  assert(std::strcmp(a->getTitle(), b->getTitle()) == 0);
  assert(std::strcmp(a->getTitle(true), b->getTitle(true)) == 0);
  assert(a->getValue() == b->getValue() && a->getDefault() == b->getDefault());
  assert(a->getMin() == b->getMin() && a->getMax() == b->getMax());
  assert(a->isPublic() == b->isPublic() && a->isStorable() == b->isStorable());
  assert(a->isMutable() == b->isMutable() &&
         a->isReadOnly() == b->isReadOnly());
  assert(a->isLinkable() == b->isLinkable() &&
         a->isUserFlag1() == b->isUserFlag1() &&
         a->isUserFlag2() == b->isUserFlag2());
  assert(!a->isOwnInfo() && !b->isOwnInfo());
  if (info.type == ParamInfo::kList) {
    auto x = ListParam::cast(a), y = ListParam::cast(b);
    assert(x && y);
    assert(x->getStringCount() == y->getStringCount());
    for (int j = 0; j < y->getStringCount(); ++j)
      assert(std::strcmp(x->getStringAt(j), y->getStringAt(j)) == 0);
  }
  char x[256], y[256];
  a->toString(x, sizeof(x));
  b->toString(y, sizeof(y));
  assert(std::strcmp(x, y) == 0);
}
} // namespace
int main(int argc, char **argv) {
  assert(argc == 2);
  Metadata data(argv[1]);
  Destruction productDestroyed, oracleDestroyed;
  for (int receiver = 0; receiver < 2; ++receiver) {
    Presonus::Mixer::MixerComponentBase mixer;
    mixer.applicationDataRoot =
        FileName((std::string(argv[1]) + "-paths").c_str());
    mixer.deviceDataFolder = "unit";
    Product product(mixer);
    auto path = product.getTempFilePath();
    assert(std::string(path.str()).find("presonus/unit/temp/mixer.scene") !=
           std::string::npos);
    Oracle oracle(data.infos.data());
    assert(std::strcmp(product.getName(), "global") == 0);
    assert(product.countParameters() == 53 && oracle.countParameters() == 53);
    for (int i = 0; i < 53; ++i) {
      auto a = product.getParameterAt(i), b = oracle.getParameterAt(i);
      equal(a, b, data.infos[i], &product, &oracle);
      a->addObserver(&productDestroyed);
      b->addObserver(&oracleDestroyed);
      assert(a == product.getParameterByTag(data.infos[i].tag));
    }
    auto source = product.getParameterByTag(20),
         destination = product.getParameterByTag(21);
    assert(ListParam::cast(source) && source->getMin() == 0 &&
           source->getMax() == 3 && source->getDefault() == 1);
    assert(destination->getType() == ParamInfo::kToggle &&
           destination->getDefault() == 0);
    for (float value : {0.f, 1.f, 2.f, 3.f}) {
      source->setValue(value, false);
      product.updateHighDef();
      assert(destination->getValue() == (value >= 2 ? 1.f : 0.f));
      product.initalize();
      assert(destination->getValue() == (value >= 2 ? 1.f : 0.f));
    }
    // Real factory parameters send feedback through their actual controllers.
    product.changes = 0;
    oracle.changes = 0;
    source->setValue(0.f, false);
    oracle.getParameterByTag(20)->setValue(0.f, false);
    source->setValue(1.f, true);
    oracle.getParameterByTag(20)->setValue(1.f, true);
    assert(product.changes == oracle.changes && product.changes > 0);
  }
  assert(productDestroyed.count == 106 && oracleDestroyed.count == 106);
  // Preserve the existing default/source-port borrowed numeric-provider domain.
  ParamInfo info = {
      ParamInfo::kInt, 20,      "sample", 0,       3,      0, 1, 1, 0,
      nullptr,         nullptr, nullptr,  nullptr, nullptr};
  NumericParam src(info), dst(info);
  Presonus::Mixer::GlobalComponent old;
  old.bindHighDefParameters(&src, &dst);
  for (float v : {0.f, 1.f, 2.f, 3.f}) {
    src.setValue(v);
    old.initalize();
    assert(dst.getValue() == (v >= 2 ? 1 : 0));
  }
  std::cout << "53 descriptors x 2 mixer receivers; factory "
               "types/metadata/controller/feedback, highDef and "
               "default-provider regression passed\n";
}
