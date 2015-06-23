#!/usr/bin/env python2
## -*- coding: utf-8 -*-
##
##  Triton tool to generate a database with the trace's information.
##  Jonathan Salwan - 2015-06-23
##
## Description:
## ------------
##
## Sometime it's useful to work offline and to apply advanced DBA
## based on a concrete trace. This tool is used to generate a database
## which will may be then loaded into several tools like IDA or may be
## used to perform more analysis. This database contains all instructions
## executed with their symbolic expressions, their memory access information
## and their registers value information.
##

from triton import *
import sqlite3

conn   = sqlite3.connect('trace.db')
cursor = conn.cursor()


def accessMemoryDump(opType, instruction, operand):

    # Checks if the source address can be read
    if checkReadAccess(operand.value):

        insAddr          = instruction.address
        accessType       = 'R'
        accessAddr       = operand.value
        accessSize       = operand.size
        contentAsString  = str()
        contentAsInteger = getMemValue(accessAddr, accessSize)

        # fills the contentAsString
        for i in range(accessSize):
            contentAsString += '%02x ' %(getMemValue(accessAddr+i, 1))

        cursor.execute("INSERT INTO memoryAccess VALUES (%d, '%s', %d, %d, '%s', %d)" %(insAddr, accessType, accessSize, accessAddr, contentAsString[:-1], contentAsInteger))

    return



def after(instruction):

    # Dump memory access when a STORE occurs
    for operand in instruction.operands:
        if operand.type == IDREF.OPERAND.MEM_W:
            accessMemoryDump(IDREF.OPERAND.MEM_W, instruction, operand)
            return

    return


def before(instruction):

    # Dump symbolic expression
    addr = instruction.address
    asm  = instruction.assembly
    seId = [se.id for se in instruction.symbolicElements]
    cursor.execute("INSERT INTO instructions VALUES (%d, '%s', '%s')" %(addr, asm, str(seId)[1:-1].replace(',','')))
    for se in instruction.symbolicElements:
        cursor.execute("INSERT INTO expressions VALUES (%d, '%s')" %(se.id, se.source))

    # Dump registers value
    for operand in instruction.operands:
        if operand.type == IDREF.OPERAND.REG:
            regId      = operand.value
            regSize    = operand.size
            regContent = getRegValue(regId)
            regName    = getRegName(regId)
            cursor.execute("INSERT INTO registersValue VALUES (%d, %d, '%s', %d, %d)" %(addr, regId, regName, regSize, regContent))

    # Dump memory access when a LOAD occurs
    for operand in instruction.operands:
        if operand.type == IDREF.OPERAND.MEM_R:
            accessMemoryDump(IDREF.OPERAND.MEM_R, instruction, operand)
            return

    return


def buildDb():
    # Instructions information
    cursor.execute("CREATE TABLE IF NOT EXISTS instructions(addr INTEGER, assembly TEXT, exprs TEXT)")
    # Symbolic expression information
    cursor.execute("CREATE TABLE IF NOT EXISTS expressions(id INTEGER PRIMARY KEY, expr TEXT)")
    # Memory access (LOAD / STORE) information
    cursor.execute("CREATE TABLE IF NOT EXISTS memoryAccess(addr INTEGER, accessType TEXT, accessSize INTEGER, accessAddr INTEGER, contentAsString TEXT, contentAsInteger INTEGER)")
    # Registers values information
    cursor.execute("CREATE TABLE IF NOT EXISTS registersValue(addr INTEGER, id INTEGER, name TEXT, size INTEGER, content INTEGER)")
    print "[+] Database created."
    return


def fini():
    conn.commit()
    conn.close()
    print "[+] Trace dumped."
    return


if __name__ == '__main__':

    # Start the symbolic analysis from the entry point
    startAnalysisFromSymbol('main')

    buildDb()

    # Add a callback.
    addCallback(before, IDREF.CALLBACK.BEFORE)
    addCallback(fini, IDREF.CALLBACK.FINI)

    # Run the instrumentation - Never returns
    runProgram()


