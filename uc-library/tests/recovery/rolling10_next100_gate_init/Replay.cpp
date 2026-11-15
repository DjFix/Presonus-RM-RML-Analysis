#include "core/portable/corecomponent.h"
#ifndef PROVIDER_ONLY
#include "presonus/surface/GatePageComponent.hpp"
#endif
#include <array>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
#ifdef PROVIDER_ONLY
using Base = Component;
#else
using Base = Presonus::Surface::GatePageComponent;
#endif
struct Registry : Base {
  void adopt(Parameter *p) { paramList.add(p); }
};
struct Observer : ParamObserverBase {
  std::array<Parameter *, 5> &objects;
  std::vector<std::string> events;
  explicit Observer(std::array<Parameter *, 5> &o) : objects(o) {}
  void paramChanged(Parameter *p, int msg) override {
    for (int i = 1; i < 5; ++i)
      if (objects[i] == p)
        events.push_back(std::to_string(i) + " " + std::to_string(msg));
  }
};
static unsigned bits(float v) {
  unsigned b;
  std::memcpy(&b, &v, 4);
  return b;
}
static float value(unsigned b) {
  float v;
  std::memcpy(&v, &b, 4);
  return v;
}
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  bool onkey = argc > 1 && std::string(argv[1]) == "--onkey";
  int kind, destination, previousMode;
  unsigned sourceBits, destinationBits, previousBits;
  while (std::cin >> kind >> destination >> previousMode >> sourceBits >>
         destinationBits >> previousBits) {
    ParamInfo sourceInfo{}, destInfo{}, oldInfo{}, aliasInfo{};
    sourceInfo.type = destInfo.type = oldInfo.type = ParamInfo::kFloat;
    sourceInfo.minValue = destInfo.minValue = oldInfo.minValue = -8;
    sourceInfo.maxValue = destInfo.maxValue = oldInfo.maxValue = 8;
    std::strcpy(sourceInfo.name, "ch_key_listen");
    std::strcpy(destInfo.name, "key_listen");
    std::strcpy(oldInfo.name, "previous");
    aliasInfo = sourceInfo;
    aliasInfo.type = ParamInfo::kAlias;
    auto sourceOwner = std::make_unique<NumericParam>(sourceInfo);
    NumericParam *source = sourceOwner.get();
    NumericParam old(oldInfo);
    auto destOwner = std::make_unique<NumericParam>(destInfo);
    NumericParam *dest = destOwner.get();
    source->setValue(value(sourceBits), false);
    dest->setValue(value(destinationBits), false);
    old.setValue(value(previousBits), false);
    Registry root;
    AliasParam *alias = nullptr;
    if (kind == 1)
      root.adopt(sourceOwner.release());
    if (kind == 2) {
      alias = new AliasParam(aliasInfo);
      alias->setOriginal(source);
      root.adopt(alias);
    }
    if (destination)
      root.adopt(destOwner.release());
    std::array<Parameter *, 5> objects{nullptr, source, dest, &old, alias};
    Observer observer(objects);
    for (int i = 1; i < 5; ++i)
      if (objects[i])
        objects[i]->addObserver(&observer);
    NumericParam *previous = previousMode == 0   ? nullptr
                             : previousMode == 1 ? source
                             : previousMode == 2 ? &old
                                                 : dest;
    auto identity = [&](Parameter *p) {
      if (!p)
        return 0;
      for (int i = 1; i < 5; ++i)
        if (p == objects[i])
          return i;
      throw std::runtime_error("unknown identity");
    };
    if (provider) {
      std::string op;
      while (std::cin >> op && op != "done") {
        if (op == "find") {
          std::string name;
          std::cin >> name;
          std::cout << identity(root.findParameter(name.c_str()));
        } else if (op == "get") {
          int i;
          std::cin >> i;
          std::cout << bits(objects.at(i)->getValue());
        } else if (op == "original") {
          int i;
          std::cin >> i;
          std::cout << identity(objects.at(i)->getOriginal());
        } else if (op == "set") {
          int i, edit;
          unsigned v;
          std::cin >> i >> v >> edit;
          objects.at(i)->setValue(value(v), edit);
          std::cout << 1;
        } else if (op == "state") {
          std::cout << bits(source->getValue()) << ' ' << bits(dest->getValue())
                    << ' ' << bits(old.getValue()) << ' '
                    << observer.events.size();
          for (auto &event : observer.events)
            std::cout << ' ' << std::quoted(event);
        } else
          throw std::runtime_error("unknown operation");
        std::cout << '\n' << std::flush;
      }
    } else {
#ifndef PROVIDER_ONLY
      root.setSourcePortPreviousOriginal(previous);
      if (onkey)
        root.onKeyListen(previousMode != 0);
      else
        root.initKeyListen();
      std::cout << identity(root.getSourcePortPreviousOriginal()) << ' '
                << bits(source->getValue()) << ' ' << bits(dest->getValue())
                << ' ' << bits(old.getValue()) << ' ' << observer.events.size();
      for (auto &event : observer.events)
        std::cout << ' ' << std::quoted(event);
      std::cout << '\n';
#else
      throw std::runtime_error("provider only");
#endif
    }
    for (int i = 1; i < 5; ++i)
      if (objects[i])
        objects[i]->removeObserver(&observer);
  }
}
