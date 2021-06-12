
int32_t Core::Text::Json::BinaryWriter::BinaryWriter(Core::IO::Stream*)(int32_t arg1, int32_t arg2)
{
    // Core::Text::Json::BinaryWriter::BinaryWriter(Core::IO::Stream*)
    *(undefined4 *)arg1 = *(undefined4 *)0x108e30;
    Core::IO::BinaryAccessor::BinaryAccessor(int)(arg1 + 4, 1);
    *(undefined4 *)(arg1 + 4) = *(undefined4 *)0x108e34;
    *(int32_t *)(arg1 + 0xc) = arg2;
    *(undefined *)(arg1 + 0x10) = 0;
    *(undefined *)(arg1 + 0x11) = 1;
    return arg1;
}


void Core::Text::Json::BinaryWriter::endArray(char const*, int)(int32_t arg1)
{
    undefined uVar1;
    int32_t iVar2;
    bool bVar3;
    undefined auStack25 [5];
    int32_t var_14h;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::endArray(char const*, int)
    uStack4 = 0x109980;
    auStack25[0] = 0x5d;
    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack25, 1);
    bVar3 = iVar2 != 1;
    if (bVar3) {
        iVar2 = 0;
    }
    uVar1 = (undefined)iVar2;
    if (!bVar3) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    return;
}

void Core::Text::Json::BinaryWriter::endObject(char const*, int)(int32_t arg1)
{
    undefined uVar1;
    int32_t iVar2;
    bool bVar3;
    undefined auStack25 [5];
    int32_t var_14h;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::endObject(char const*, int)
    uStack4 = 0x1099d0;
    auStack25[0] = 0x7d;
    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack25, 1);
    bVar3 = iVar2 != 1;
    if (bVar3) {
        iVar2 = 0;
    }
    uVar1 = (undefined)iVar2;
    if (!bVar3) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    return;
}

void Core::Text::Json::BinaryWriter::setNullValue(char const*, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t arg2_00;
    int32_t iVar2;
    bool bVar3;
    undefined uStack35;
    undefined uStack34;
    undefined auStack33 [4];
    int32_t var_1dh;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::setNullValue(char const*, int)
    uStack4 = 0x109a20;
    if ((arg2 != 0) && (arg2_00 = strlen(arg2), 0 < (int32_t)arg2_00)) {
        if (arg2_00 + 0x80 < 0x100) {
            uStack35 = 0x69;
            uStack34 = (char)arg2_00;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack35, 2);
        } else {
            if (arg2_00 < 0x100) {
                uStack35 = 0x55;
                uStack34 = (char)arg2_00;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack35, 2);
            } else {
                if (arg2_00 + 0x8000 < 0x10000) {
                    auStack33[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(arg2_00 * 0x10000) >> 0x10);
                } else {
                    auStack33[0] = 0x6c;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, arg2_00);
                }
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
    }
    auStack33[0] = 0x5a;
    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
    bVar3 = iVar2 != 1;
    if (bVar3) {
        iVar2 = 0;
    }
    uVar1 = (undefined)iVar2;
    if (!bVar3) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    return;
}

void Core::Text::Json::BinaryWriter::setValue(char const*, bool, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t arg2_00;
    int32_t iVar2;
    int32_t in_r2;
    bool bVar3;
    undefined uStack43;
    undefined uStack42;
    undefined auStack41 [4];
    int32_t var_25h;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::setValue(char const*, bool, int)
    uStack4 = 0x109fc4;
    if ((arg2 != 0) && (arg2_00 = strlen(arg2), 0 < (int32_t)arg2_00)) {
        if (arg2_00 + 0x80 < 0x100) {
            uStack43 = 0x69;
            uStack42 = (char)arg2_00;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
        } else {
            if (arg2_00 < 0x100) {
                uStack43 = 0x55;
                uStack42 = (char)arg2_00;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
            } else {
                if (arg2_00 + 0x8000 < 0x10000) {
                    auStack41[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(arg2_00 * 0x10000) >> 0x10);
                } else {
                    auStack41[0] = 0x6c;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, arg2_00);
                }
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
    }
    if (in_r2 == 0) {
        auStack41[0] = 0x46;
    } else {
        auStack41[0] = 0x54;
    }
    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
    bVar3 = iVar2 != 1;
    if (bVar3) {
        iVar2 = 0;
    }
    uVar1 = (undefined)iVar2;
    if (!bVar3) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    return;
}


void Core::Text::Json::BinaryWriter::setValue(char const*, char const*, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t uVar2;
    int32_t iVar3;
    uint32_t in_r2;
    bool bVar4;
    undefined uStack43;
    undefined uStack42;
    undefined auStack41 [4];
    int32_t var_25h;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::setValue(char const*, char const*, int)
    uStack4 = 0x10a16c;
    if ((arg2 != 0) && (uVar2 = strlen(arg2), 0 < (int32_t)uVar2)) {
        if (uVar2 + 0x80 < 0x100) {
            uStack43 = 0x69;
            uStack42 = (char)uVar2;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
        } else {
            if (uVar2 < 0x100) {
                uStack43 = 0x55;
                uStack42 = (char)uVar2;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
            } else {
                if (uVar2 + 0x8000 < 0x10000) {
                    auStack41[0] = 0x49;
                    iVar3 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar4 = iVar3 != 1;
                    if (bVar4) {
                        iVar3 = 0;
                    }
                    uVar1 = (undefined)iVar3;
                    if (!bVar4) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(uVar2 * 0x10000) >> 0x10);
                } else {
                    auStack41[0] = 0x6c;
                    iVar3 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar4 = iVar3 != 1;
                    if (bVar4) {
                        iVar3 = 0;
                    }
                    uVar1 = (undefined)iVar3;
                    if (!bVar4) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, uVar2);
                }
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, uVar2);
    }
    if (in_r2 == 0) {
        uVar2 = 0x80;
    } else {
        in_r2 = strlen();
        uVar2 = in_r2 + 0x80;
    }
    auStack41[0] = 0x53;
    iVar3 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
    bVar4 = iVar3 != 1;
    if (bVar4) {
        iVar3 = 0;
    }
    uVar1 = (undefined)iVar3;
    if (!bVar4) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    if (uVar2 < 0x100) {
        uStack43 = 0x69;
        uStack42 = (char)in_r2;
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
    } else {
        if (in_r2 < 0x100) {
            uStack43 = 0x55;
            uStack42 = (char)in_r2;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
        } else {
            if (in_r2 + 0x8000 < 0x10000) {
                auStack41[0] = 0x49;
                iVar3 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                bVar4 = iVar3 != 1;
                if (bVar4) {
                    iVar3 = 0;
                }
                uVar1 = (undefined)iVar3;
                if (!bVar4) {
                    uVar1 = 1;
                }
                *(undefined *)(arg1 + 0x11) = uVar1;
                Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(int16_t)in_r2);
            } else {
                auStack41[0] = 0x6c;
                iVar3 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                bVar4 = iVar3 != 1;
                if (bVar4) {
                    iVar3 = 0;
                }
                uVar1 = (undefined)iVar3;
                if (!bVar4) {
                    uVar1 = 1;
                }
                *(undefined *)(arg1 + 0x11) = uVar1;
                Core::IO::BinaryAccessor::write(int)(arg1 + 4, in_r2);
            }
        }
    }
    if (0 < (int32_t)in_r2) {
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc));
    }
    return;
}

void Core::Text::Json::BinaryWriter::setValue(char const*, double, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t arg2_00;
    int32_t iVar2;
    int32_t in_r2;
    uint32_t in_r3;
    bool bVar3;
    undefined uStack51;
    undefined uStack50;
    undefined auStack49 [4];
    int32_t var_2dh;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::setValue(char const*, double, int)
    uStack4 = 0x10a454;
    if ((arg2 != 0) && (arg2_00 = strlen(arg2), 0 < (int32_t)arg2_00)) {
        if (arg2_00 + 0x80 < 0x100) {
            uStack51 = 0x69;
            uStack50 = (char)arg2_00;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack51, 2);
        } else {
            if (arg2_00 < 0x100) {
                uStack51 = 0x55;
                uStack50 = (char)arg2_00;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack51, 2);
            } else {
                if (arg2_00 + 0x8000 < 0x10000) {
                    auStack49[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack49, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(arg2_00 * 0x10000) >> 0x10);
                } else {
                    auStack49[0] = 0x6c;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack49, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, arg2_00);
                }
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
    }
    if (*(char *)(arg1 + 0x10) == '\0') {
        auStack49[0] = 100;
        iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack49, 1);
        bVar3 = iVar2 != 1;
        if (bVar3) {
            iVar2 = 0;
        }
        uVar1 = (undefined)iVar2;
        if (!bVar3) {
            uVar1 = 1;
        }
        *(undefined *)(arg1 + 0x11) = uVar1;
        iVar2 = __truncdfsf2(in_r2, in_r3);
        Core::IO::BinaryAccessor::write(float)(arg1 + 4, iVar2);
    } else {
        auStack49[0] = 0x44;
        iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack49, 1);
        bVar3 = iVar2 != 1;
        if (bVar3) {
            iVar2 = 0;
        }
        uVar1 = (undefined)iVar2;
        if (!bVar3) {
            uVar1 = 1;
        }
        *(undefined *)(arg1 + 0x11) = uVar1;
        Core::IO::BinaryAccessor::write(double)(arg1 + 4);
    }
    return;
}

void Core::Text::Json::BinaryWriter::setValue(char const*, long long, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t arg2_00;
    int32_t iVar2;
    uint32_t in_r2;
    int32_t in_r3;
    bool bVar3;
    undefined uStack43;
    undefined uStack42;
    undefined auStack41 [5];
    int32_t var_24h;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::setValue(char const*, long long, int)
    uStack4 = 0x10a678;
    if ((arg2 != 0) && (arg2_00 = strlen(arg2), 0 < (int32_t)arg2_00)) {
        if (arg2_00 + 0x80 < 0x100) {
            uStack43 = 0x69;
            uStack42 = (char)arg2_00;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
        } else {
            if (arg2_00 < 0x100) {
                uStack43 = 0x55;
                uStack42 = (char)arg2_00;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
            } else {
                if (arg2_00 + 0x8000 < 0x10000) {
                    auStack41[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(arg2_00 * 0x10000) >> 0x10);
                    (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
                    goto joined_r0x0010a804;
                }
                auStack41[0] = 0x6c;
                iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                bVar3 = iVar2 != 1;
                if (bVar3) {
                    iVar2 = 0;
                }
                uVar1 = (undefined)iVar2;
                if (!bVar3) {
                    uVar1 = 1;
                }
                *(undefined *)(arg1 + 0x11) = uVar1;
                Core::IO::BinaryAccessor::write(int)(arg1 + 4, arg2_00);
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
    }
joined_r0x0010a804:
    if ((in_r3 + (uint32_t)(0x80000000 < in_r2) == 0) && (in_r2 != 0x80000000)) {
        if (in_r2 + 0x80 < 0x100) {
            uStack43 = 0x69;
            uStack42 = (char)in_r2;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
        } else {
            if (in_r2 < 0x100) {
                uStack43 = 0x55;
                uStack42 = (char)in_r2;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack43, 2);
            } else {
                if (in_r2 + 0x8000 < 0x10000) {
                    auStack41[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(int16_t)in_r2);
                } else {
                    auStack41[0] = 0x6c;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, in_r2);
                }
            }
        }
    } else {
        auStack41[0] = 0x4c;
        iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack41, 1);
        bVar3 = iVar2 != 1;
        if (bVar3) {
            iVar2 = 0;
        }
        uVar1 = (undefined)iVar2;
        if (!bVar3) {
            uVar1 = 1;
        }
        *(undefined *)(arg1 + 0x11) = uVar1;
        Core::IO::BinaryAccessor::write(long long)(arg1 + 4);
    }
    return;
}

void Core::Text::Json::BinaryWriter::startArray(char const*, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t arg2_00;
    int32_t iVar2;
    bool bVar3;
    undefined uStack35;
    undefined uStack34;
    undefined auStack33 [4];
    int32_t var_1dh;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::startArray(char const*, int)
    uStack4 = 0x109bbc;
    if ((arg2 != 0) && (arg2_00 = strlen(arg2), 0 < (int32_t)arg2_00)) {
        if (arg2_00 + 0x80 < 0x100) {
            uStack35 = 0x69;
            uStack34 = (char)arg2_00;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack35, 2);
        } else {
            if (arg2_00 < 0x100) {
                uStack35 = 0x55;
                uStack34 = (char)arg2_00;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack35, 2);
            } else {
                if (arg2_00 + 0x8000 < 0x10000) {
                    auStack33[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(arg2_00 * 0x10000) >> 0x10);
                } else {
                    auStack33[0] = 0x6c;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, arg2_00);
                }
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
    }
    auStack33[0] = 0x5b;
    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
    bVar3 = iVar2 != 1;
    if (bVar3) {
        iVar2 = 0;
    }
    uVar1 = (undefined)iVar2;
    if (!bVar3) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    return;
}

void Core::Text::Json::BinaryWriter::startObject(char const*, int)(int32_t arg1, int32_t arg2)
{
    undefined uVar1;
    uint32_t arg2_00;
    int32_t iVar2;
    bool bVar3;
    undefined uStack35;
    undefined uStack34;
    undefined auStack33 [4];
    int32_t var_1dh;
    undefined4 uStack4;
    
    // Core::Text::Json::BinaryWriter::startObject(char const*, int)
    uStack4 = 0x109d58;
    if ((arg2 != 0) && (arg2_00 = strlen(arg2), 0 < (int32_t)arg2_00)) {
        if (arg2_00 + 0x80 < 0x100) {
            uStack35 = 0x69;
            uStack34 = (char)arg2_00;
            (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack35, 2);
        } else {
            if (arg2_00 < 0x100) {
                uStack35 = 0x55;
                uStack34 = (char)arg2_00;
                (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), &uStack35, 2);
            } else {
                if (arg2_00 + 0x8000 < 0x10000) {
                    auStack33[0] = 0x49;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(short)(arg1 + 4, (int32_t)(arg2_00 * 0x10000) >> 0x10);
                } else {
                    auStack33[0] = 0x6c;
                    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
                    bVar3 = iVar2 != 1;
                    if (bVar3) {
                        iVar2 = 0;
                    }
                    uVar1 = (undefined)iVar2;
                    if (!bVar3) {
                        uVar1 = 1;
                    }
                    *(undefined *)(arg1 + 0x11) = uVar1;
                    Core::IO::BinaryAccessor::write(int)(arg1 + 4, arg2_00);
                }
            }
        }
        (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), arg2, arg2_00);
    }
    auStack33[0] = 0x7b;
    iVar2 = (**(code **)(**(int32_t **)(arg1 + 0xc) + 0x14))(*(int32_t **)(arg1 + 0xc), auStack33, 1);
    bVar3 = iVar2 != 1;
    if (bVar3) {
        iVar2 = 0;
    }
    uVar1 = (undefined)iVar2;
    if (!bVar3) {
        uVar1 = 1;
    }
    *(undefined *)(arg1 + 0x11) = uVar1;
    return;
}


