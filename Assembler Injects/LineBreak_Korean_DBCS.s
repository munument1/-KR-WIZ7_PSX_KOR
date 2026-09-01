.set noreorder
.set noat
.text
.globl FUN_strchr_dbcs

# Drop-in replacement for the English patch's FUN_strchr line-wrap helper.
# ABI: a0=string, a1=delimiter (normally ASCII space), v0=byte offset or -1.
# Korean/native PSX DBCS leads 0x80..0x9F consume two bytes but count as one
# logical display character. The returned offset remains a raw byte offset.
FUN_strchr_dbcs:
    move  $t0,$zero          # byte offset
    move  $t1,$zero          # logical character position
    move  $t2,$zero          # previous matching byte offset
    andi  $a1,$a1,0xff
loop:
    addu  $t3,$a0,$t0
    lbu   $t4,0($t3)
    beq   $t4,$zero,end_string
    nop

    bne   $t4,$a1,advance
    nop
    slti  $t5,$t1,16
    bne   $t5,$zero,save_match
    nop
    move  $v0,$t2
    jr    $ra
    nop
save_match:
    move  $t2,$t0

advance:
    addiu $t5,$t4,-0x80
    sltiu $t5,$t5,0x20       # native lead 0x80..0x9F
    beq   $t5,$zero,advance_ascii
    nop
    addiu $t0,$t0,2
    addiu $t1,$t1,1
    b     loop
    nop
advance_ascii:
    addiu $t0,$t0,1
    addiu $t1,$t1,1
    b     loop
    nop

end_string:
    beq   $t2,$zero,no_break
    nop
    slti  $t5,$t1,16
    beq   $t5,$zero,return_prev
    nop

    addu  $t3,$a0,$t2
    lbu   $t4,1($t3)
    addiu $t5,$zero,33        # !
    beq   $t4,$t5,return_prev
    nop
    addiu $t5,$zero,37        # %
    beq   $t4,$t5,return_prev
    nop
    addiu $t5,$zero,38        # &
    beq   $t4,$t5,return_prev
    nop
    addiu $t5,$zero,93        # ]
    beq   $t4,$t5,return_prev
    nop
    addiu $t5,$zero,64        # @
    beq   $t4,$t5,return_prev
    nop
    addiu $t5,$zero,35        # #
    beq   $t4,$t5,return_prev
    nop
    addiu $t5,$zero,124       # |
    beq   $t4,$t5,return_prev
    nop

no_break:
    addiu $v0,$zero,-1
    jr    $ra
    nop
return_prev:
    move  $v0,$t2
    jr    $ra
    nop
