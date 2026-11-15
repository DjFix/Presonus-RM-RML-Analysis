#include "presonus/MackieControlComponent.hpp"
#include <bit>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using namespace Core::Portable;
struct Page : Presonus::MackieControlComponent {
  ParamList &list() { return paramList; }
};
struct Observer : ParamObserverBase {
  std::vector<Parameter *> &params;
  std::vector<std::string> &events;
  Observer(std::vector<Parameter *> &p, std::vector<std::string> &e)
      : params(p), events(e) {}
  void paramChanged(Parameter *p, int msg) override {
    std::ostringstream s;
    s << "S";
    for (unsigned i = 0; i < params.size(); ++i)
      if (params[i] == p)
        s << i;
    s << ':' << msg;
    for (auto *q : params)
      s << ':' << std::bit_cast<std::uint32_t>(q->getValue());
    events.push_back(s.str());
  }
};
int main(int argc, char **argv) {
  const bool provider = argc > 1 && std::string(argv[1]) == "provider";
  int kind, scenario;
  if (!(std::cin >> kind >> scenario))
    return 2;
  Page page;
  std::vector<Parameter *> params;
  std::vector<std::unique_ptr<ParamInfo>> infos;
  std::vector<std::string> events;
  Observer observer(params, events);
  auto add = [&](int tag) {
    auto info = std::make_unique<ParamInfo>();
    *info = {};
    info->type = ParamInfo::kFloat;
    info->tag = tag;
    info->minValue = -10;
    info->maxValue = 30;
    info->defaultValue = 2;
    if (kind == 2 && scenario == 1) {
      info->minValue = 0;
      info->maxValue = 1;
      info->defaultValue = .25f;
    }
    if (kind == 3) {
      info->minValue = -33554432.f;
      info->maxValue = 33554432.f;
    }
    auto *p = new NumericParam(*info);
    infos.push_back(std::move(info));
    params.push_back(p);
    page.list().add(p);
    p->addObserver(&observer);
  };
  int base = kind == 0 ? 0x2000 : 0;
  if (kind < 2) {
    if (scenario == 0 || scenario == 5 || scenario == 6) {
      add(base);
      add(base + 1);
      add(base + 7);
    } else if (scenario == 1)
      add(base + 1);
    else if (scenario == 2) {
      add(base);
      add(base + 99);
    } else if (scenario == 3) {
      add(base + 7);
      add(base);
      add(base + 1);
    }
    if (scenario == 5)
      add(0x9000);
  } else if (kind == 3) {
    int mask = scenario & 7;
    if (scenario == 8 || scenario == 9 || scenario == 10)
      mask = 7;
    if (scenario == 9) {
      add(0x4600);
      add(0x4500);
      add(0x4400);
      add(0x4401);
    } else
      for (int stage = 0; stage < 3; ++stage)
        if (mask & (1 << stage)) {
          add(0x4400 + stage * 0x100);
          if (scenario == 10)
            add(0x5500 + stage);
        }
  } else {
    add(scenario == 1 ? 0x9000 : 0x2000);
  }
  ParamArrayAccessor fader(0x2000), meter(0), mode(0x4400), value(0x4500),
      flag(0x4600);
  auto access = [&](int stage) -> ParamArrayAccessor & {
    if (stage == 0)
      return fader;
    if (stage == 1)
      return meter;
    if (stage == 2)
      return mode;
    if (stage == 3)
      return value;
    return flag;
  };
  auto id = [&](Parameter *p) {
    for (unsigned i = 0; i < params.size(); ++i)
      if (params[i] == p)
        return int(i);
    return -1;
  };
  Parameter **array = nullptr;
  Parameter *saved = nullptr;
  int changedIndex = -1;
  auto restore = [&]() {
    if (array && changedIndex >= 0) {
      array[changedIndex] = saved;
      array = nullptr;
      changedIndex = -1;
    }
  };
  for (auto &v : page.model.faderValues)
    v = -1;
  page.model.midiSink = [&](const unsigned char *b, unsigned n, unsigned port) {
    std::ostringstream s;
    s << "M:" << port;
    for (unsigned i = 0; i < n; ++i)
      s << ':' << unsigned(b[i]);
    events.push_back(s.str());
  };
#ifndef PROVIDER_ONLY
  if (kind == 0 && scenario == 5)
    page.masterFader = NumericParam::cast(params.back());
#endif
  std::string op;
  while (std::cin >> op) {
    int stage = 0, offset = 0, which = 0, msg = 0;
    std::uint32_t bits = 0;
    if (op == "ERROR") {
      std::cout << id(page.list().at(-1)) << std::endl;
      continue;
    }
    if (op == "LIST") {
      std::cout << page.list().count();
      for (int i = 0; i < page.list().count(); ++i)
        std::cout << ' ' << id(page.list().at(i));
      std::cout << std::endl;
      continue;
    }
    if (op == "TAG") {
      std::cin >> which;
      std::cout << params.at(which)->getTag() << std::endl;
      continue;
    }
    if (op == "INDEX") {
      std::cin >> which;
      std::cout << page.list().getIndexByTag(which) << std::endl;
      continue;
    }
    if (op == "GET") {
      std::cin >> stage >> offset;
      std::cout << id(access(stage).getAt(page.list(), offset)) << std::endl;
      continue;
    }
    if (op == "SET") {
      std::cin >> which >> bits >> stage;
      if (stage)
        params.at(which)->setNormalized(std::bit_cast<float>(bits), false);
      else
        params.at(which)->setValue(std::bit_cast<float>(bits), false);
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "NORMAL") {
      std::cin >> which;
      std::cout << std::bit_cast<std::uint32_t>(
                       params.at(which)->getNormalized())
                << std::endl;
      continue;
    }
    if (op == "TOUCH") {
      std::cin >> which >> msg;
      page.model.touchFader(which, msg != 0);
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "MOVE") {
      std::cin >> which >> bits;
      page.model.moveFader(which, std::bit_cast<float>(bits));
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "ADDBARS") {
      for (int b : {0x4400, 0x4500, 0x4600})
        if (page.list().getIndexByTag(b) == -1)
          add(b);
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "APPEND") {
      add(base);
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "ALIAS" || op == "NULL") {
      restore();
      array = page.list();
      changedIndex = page.list().count() - 1;
      saved = array[changedIndex];
      array[changedIndex] = op == "ALIAS" ? params.front() : nullptr;
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "CALL") {
      int tag, modeInput;
      unsigned boolInput;
      std::cin >> tag >> modeInput >> bits >> boolInput >> msg;
#ifndef PROVIDER_ONLY
      if (kind == 0)
        page.updateFader(tag, std::bit_cast<float>(bits));
      else if (kind == 1)
        page.updateMeter(tag, std::bit_cast<float>(bits));
      else if (kind == 2) {
        infos[0]->tag = tag;
        params[0]->setNormalized(std::bit_cast<float>(bits), false);
        events.clear();
        page.paramChanged(params[0], msg);
      } else
        page.updateValueBar(tag, modeInput, std::bit_cast<float>(bits),
                            boolInput != 0);
#else
      return 4;
#endif
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "INPUT") {
      int tag;
      std::cin >> tag >> bits;
      infos[0]->tag = tag;
      params[0]->setNormalized(std::bit_cast<float>(bits), false);
      events.clear();
      std::cout << 1 << std::endl;
      continue;
    }
    if (op == "REPORT") {
      std::cout << params.size();
      for (auto *p : params)
        std::cout << ' ' << std::bit_cast<std::uint32_t>(p->getValue());
      std::cout << " |";
      for (auto t : page.model.touched)
        std::cout << ' ' << unsigned(t);
      for (auto v : page.model.faderValues)
        std::cout << ' ' << v;
      std::cout << " |";
      for (auto &e : events)
        std::cout << ' ' << e;
      std::cout << std::endl;
      continue;
    }
    return 3;
  }
  restore();
  for (auto *p : params)
    p->removeObserver(&observer);
  // CCL Component owns parameters; metadata stays live through their
  // destruction. Explicitly remove while metadata and observer vectors are
  // valid.
  for (auto *p : params) {
    page.list().remove(p);
    delete p;
  }
}
