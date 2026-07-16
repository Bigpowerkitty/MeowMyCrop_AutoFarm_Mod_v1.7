param(
    [ValidateSet("Install", "Speed", "Uninstall")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $packageRoot "mod_manager.log"
$relativeTarget = "MeowMyCrop_Data\Managed\Assembly-CSharp.dll"
$originalHash = "ad00d6dd37d0ee222e5506e9a4b697c5b5bf10fa3673843cde68b9760654e954"
$legacyV10Hash = "6a9d6571fa9cf6f24194b565f18c5e4633941311929a929fdaf1fe70c8d6f9f2"
$variantHashes = @{
    "1" = "735c86b2352542ed64f311bc33aeae450722b9ebe2400233155a57897293aea6"
    "2" = "c490741c09105c593a98ba1e8b26d63dcfd7a85434399f7c59bc01d371f8df01"
    "5" = "9ffb983374d9dd7104e0906e30b5d9958978be2ccc63f853ec65623dbebafaf7"
    "10" = "debf111307d5c622d84949cb120cac7a4e84d79aae42a122c375dff9458e82af"
    "20" = "346f570f10d6f9c430755aa68aad10dacbbd1e9eb5aaacf16790125cfe08f5b9"
    "50" = "16a6d3b5971cbe2a168478ab83307841a6739bbb2aabab8ab9929995b3bcccfb"
    "500" = "de750fd3cff524d98818185d0be7a6295a0f48429c2f17a5e3f657440fc113ab"
}

$legacyV17LatestHashes = @{
    "1" = "feb56d45cedf8fb5cfacc4c7101d2b217e857993ef06853fe351dc7d81ec3ff6"
    "2" = "bb3f13758ae632327dfe5d752c8ce6e1f9deaebd891737ef46387dc0323926bd"
    "5" = "16b537b40498aaac76af6a78c92579eec1d117ddebce65f13d17e49b69971455"
    "10" = "d0c65db7e12fb09025c137213b1bd938b68ab30b1019f2c53a7c0218fedb73a5"
    "20" = "6ab468ae082eecd26a704b930bcb2a45eab87cfaa8091b1b68979984e326653d"
    "50" = "4b63e999e6fbd2650b40df21828fe66c866ce05499707e268833152b990fec88"
    "500" = "551b9cf45dd20e9d30858ee38066e794664f897db3beb45ea9ce144d9dca7af2"
}

$legacyV17OriginalInstanceHashes = @{
    "1" = "a5f2e9eb1fab657808c78f5ba117169ba7fed3cf27b7a26348f7fa089bc89278"
    "2" = "28827fe4b778f7864332537c0a16e173623e902beaa8f67be5ce6fda290d0531"
    "5" = "5e266a8e35b2a9a2a0314e3d6bffd7235c252fab0a35f75d44d92ed410293165"
    "10" = "ba903f58dcaa37aa299bd962010f91ce9c99ae525ec6f188879f32cc9f0176d5"
    "20" = "b45118ea179409cba11b6f42307613da378b1916593af0e10a58ba7824bf381e"
    "50" = "7cef4a7114de57bead9f44dbf87431ee249042c03a8d1a3f2e12d22b655fa3eb"
    "500" = "d36300c70ca729b687abf7ab50ee46d54eb2ff971893876ee4418fa180237449"
}

$legacyV17AutoSupplyRefreshHashes = @{
    "1" = "1e63051560518f90dbbd1477e54dcf87ab958a251d697722654268be380f3baf"
    "2" = "aee7c393ece6e139c78285fe36c9b0930d7007f29a8737bae968bcbc31ddf2a7"
    "5" = "48de46ca8b3c59d07e823b395a6f1a79341e93c295e2b1459d7f96ae158f17a5"
    "10" = "60fe0f355c9b9ab888e379becd7113bd285aab793d4aa7767557e0784a3f2918"
    "20" = "969da09b04f016048b9a4100c9cf1c20de827d8ab42ac33e9ea5338570947246"
    "50" = "6468f3a6084a82c984346b714c0d9371a16826333acb4a4cee44d8d1ece10279"
    "500" = "da116ae10b8e4f31c4d4182cf4088c4e665b6d415900c85e6a9939703d8749c9"
}

$legacyV17StartupAutoOnHashes = @{
    "1" = "842f8ac8b2f03ded83d568cb702271879d0d975b203d0632c3361dcc1ec33819"
    "2" = "88680ec8c011459ed41c61116ee7384376e60057d1e410a203dc23490ceb2791"
    "5" = "888eedc480fbc3e2899e49ff6a3ec37865c40d4fc95aa86406adb3a3da005333"
    "10" = "c5d103bf2b5a4b77c51be17b12a820022bfed66f02da65736f9ed1f9da568f3f"
    "20" = "167250f9e74047654a4dcacb2de04955e334273209d425eb056fd935a9a0ffd7"
    "50" = "8d47b789e9bc2550f9d97d4184f0e6c9cdf3f430eadd03cb450fa8dd32c2e30c"
    "500" = "8f18285f4599146bf99ad608eb559d29c65a8cb5d1088f0b36eb71b46b662f7c"
}

$legacyV17VisibleActiveHashes = @{
    "1" = "a7797df3c2cd8b669664f0a2fedff2dc9221bdaa4e986c39d38989885d4b95c6"
    "2" = "411656a0d1f66494fa518e180c1141d6d2b4fdfbec092c78049bd4193ab57652"
    "5" = "6c0c62043b66bc10c4af5db66e279a365ae1eac4fd37e80f5c953bc8d78a6bf3"
    "10" = "4ca37ea70b3ac2e7b5753b569c5c65ed9288da7e9bf2a9a0c5da3d662982b89b"
    "20" = "7faa42f10e8997ff1b46beebd7f30e1a9218b04a0801fc64a6e1857059bf397b"
    "50" = "ee2120a5570e552afb7cc239755f8fcbcbdb94c6cf2803368be0c588e8c19cbf"
    "500" = "d26b32d0eac91dde0ad99c0ca5c259c3d59dd9071550b236b2094760f8fa0ad2"
}

$legacyV17VisibleFruitOnlyHashes = @{
    "1" = "209e88552fd0b4b104c2888785c7755e0a3a3dbf764be7cd4d01acd00d831665"
    "2" = "ff5327de56a97f199e5d3a1e86d1b7fb6b09fc9bb2d7d2af5b0fae2a3fcaad13"
    "5" = "d68d5e33f1d05bb6f7142c35c814fc2a6be09b4b972c35acc310e3845ddc5ec8"
    "10" = "1eac51069233897e02f967aaa033109a3a35d266144bacfcdac1ef96dc766659"
    "20" = "00a983be0fe6011d72d2e89af2e91303dc3d76c3dc44fb5cfafc17a46fcd177b"
    "50" = "c51912e8f4038418e159cd2a3a31e98cf0c91d30d63cbaa78cda22f62ee38c81"
    "500" = "344ccaa809e74184730ca03771ffb1e6bd3f3bffb6999fed9e4720e19b637023"
}

$legacyV17FruitTokenGateHashes = @{
    "1" = "0de6a4bfcf87b0536c34a76fa9ccae7200dce678b40c2f6297cae17ea83a4b65"
    "2" = "3eae4d829237982bfdf94304481cd853e4f0555be781ee9b288c34bbd668032d"
    "5" = "1cd4b64cccf837c4a4952366c283c3fd91e899767ce793a187822fe0e6b6bc9c"
    "10" = "afe38cd6bae34aeb14c197066577b17eecfa5ed061d35b7f37eb81e6e84b208f"
    "20" = "b83d0eea31eaea12ad7afdc93788867dc83d3e40528e77b301cb8f5232548595"
    "50" = "88c440235d729a0c1e730f2f4d3908879e334d6951c97837034c5c659350f301"
    "500" = "960cda4583a0513ecbd5ae6835d9f5dcf4df6cf4a75043747487a69195d8ea0c"
}

$legacyV17AutoCanEventLockHashes = @{
    "1" = "8ee562eee6206caf87da9961091c446d9ddd21e87cc919ec5a5a5b99531c9088"
    "2" = "fb1def44c9f5f4641ea7686b64ed7a7eb2daa452a76631f21a51e3aa708d11e0"
    "5" = "012c5b46bfda7b1a2fb0e28a0695fb0b6377678385cab6401baa72a73f2ff73d"
    "10" = "81061028735edab8e72fcb1a0a14a5215c5885da6ab3090ebd8c72edaeb1a346"
    "20" = "eab0a06465f2eeb00a09db135a69e4f90ad7b5839b0c48180e06e95088a99db9"
    "50" = "f431d55e3bc80f76997ed6f6e34d4b79c777a28127e3107e11b564db2839b372"
    "500" = "af497907fc473705ca9a94e3922c9ed23fef325e4a16afce5fdb7d6cc691bf41"
}

$legacyV17AutoCanFilteredInstanceHashes = @{
    "1" = "cc12ddf63d2c21ddc4b0cd827418919be7b922f213eaa95f4b9def5f912bfb40"
    "2" = "42b02b802015268adde12808cbf21f437f810afaf6df3288bb6ac4ef1235ad15"
    "5" = "92eb78bceb77ecc02bce0e5f4e647baa435c0a1d7e2ca3be19bf334bff120685"
    "10" = "245617b29afbb45003e5fb2f86d94e6d7f2e8ceef5df71af75935b6f34ebe48a"
    "20" = "97686f780cd1baec33a27ddf84e6ad08c2bf657fe24863e381cda2230467741a"
    "50" = "840cba40ceeeb1953a13b4eae1f7a29a4d2f30cf3f7aa0288e667238c2c4c626"
    "500" = "6d811e5f02d54a5d6f9297ea8060283a814da3c5692c54096a1a75707fb9bfba"
}

$legacyV17AutoCanSharedEntryGuardHashes = @{
    "1" = "ff653e8e5d968e5ddc0b8d42780797c095da8f3b2a92196d8c10eadef1c35524"
    "2" = "470b13e6e8ddbd17abe023f7f1ead06f22f54efd609826523cdc416084128a7a"
    "5" = "6a63f18e03fe174613bd5d31cce01202e29cae3dccf7197dde69d15bbec80c75"
    "10" = "d2102968e191366f430ae887f46983ca7c80c2aac92698022e5e916f4f8a2a7c"
    "20" = "b6e8618e5c5e8563fdcd5b8b35f66bccc66c0844607423d7641d5e7c74fba94f"
    "50" = "992423c9355046eb5938bef362256144ed71b9a2edac8f72908adb0d252824ce"
    "500" = "08f5c5f0947b1ab1a22820e1289151883ef86fdb688211be92b0fac77ea600a4"
}

$legacyV17AutoCanEntryGuardHashes = @{
    "1" = "9c9d444b8c93062141ccb39faeb43062b2dc24bb5592ed548ab9395d3b40d1c8"
    "2" = "23a21b956de51d235521d0410713bd38b3c8037f0f5335a46b70262abd11f947"
    "5" = "b15e23dddf75562f2a92af8aec465014eb675910949559034a05f891286be289"
    "10" = "b4fd13873a14894dd4be0eef14c1b0b1f67a01681ad9bc1f86a2bbcc6fa02630"
    "20" = "53c40fec9eaed6a2d95463d17acfd9db06c2cba6cecd8b1b4c23a9a1f6206237"
    "50" = "d6752629abd9989831f4cd29bd255c9e251526e610c34c937be68a0fac233cc8"
    "500" = "9c4b45c40c80e53695fb366a805c42bfd9112f0e5e39b1cacbc1abe4a6c61088"
}

$legacyV17AutoCanRefreshAccessHashes = @{
    "1" = "d48644adb5a4d1c8d7d1181c7ceda3666e93375cadf647170ef5e7ffd7273a93"
    "2" = "998de791e226b9b1b5112a87b0ae79de83140ea3f6b42df212887959f18cee6e"
    "5" = "204d6ab316ff23c43bce5b10f63fde17b52eabddff0fd476fa8856f52799d97f"
    "10" = "6f6f536d24e21ed3e8c8c9ef06a970ddb2c7264c971d3942abaf04c1f388f85f"
    "20" = "d62fb064e7fdab0843f626b9ebdccbd66c47ed803a857ef6af66f2bf43509e25"
    "50" = "781910d8659a1ffeecf786bc62aa70dbdd36229dc84dee0ebea799ccefd812f6"
    "500" = "568c54de3303c7d682390c2eab20f6cd3edcbc94cf30364fc1fa280dcf48021c"
}

$legacyV17AutoCanGuardHashes = @{
    "1" = "fd6acf0ea9d49185c835a0294199b99079c4c1a2c26ea1c74eee9c1e7616fba8"
    "2" = "a8a2785d186e21edbe7efdf072f838bcc2e086f1255305a229609d30778b1bd1"
    "5" = "527a38fbbbf0aa39a7c15a1285ebda6390f057d191be322fe5018132fa5b3efe"
    "10" = "99c8e58ec7f0cacbf083b0a56e2a665443455d086aa1760e0df2d1024803ccd3"
    "20" = "6a1cd0cf479f5c22810d8564a011ffa8bb534a9075db492a1e46fb32a6048f35"
    "50" = "ac836311c52e12bef8f8b25461a8a46cb57d4f68d5a99761066a41f54ab037c4"
    "500" = "4fd4bcb0d316faed686a4bcee791985d4193be451fcbf8d04722f2921c274625"
}

$legacyV17AutoSupplyReentryHashes = @{
    "1" = "0ff08cd4ffc52b5b6ca60ac7d4ac588d9088f981789cd33ec1fdabb0233c96b4"
    "2" = "65bb1d0b5239c0400697e6e1253245ca73ea90e0ff7f113d1ba00d99e5e7dc17"
    "5" = "1aa5ef1b53740718b55f7f074f0409ea34d9ef19cddd9ec7c461250191cd99a3"
    "10" = "1e6e870dc1290fc0c91f7e40d64685717cb628a8ba5afa41f3ba65cbd06a0948"
    "20" = "02baf004ccae110f9d014c7eb288de62d6665a4dd5c02081e11192c9d874b4fd"
    "50" = "14ec38d2c8fa6160d85ab7c157dc1a72b51c7573cd668167205105efc4bd6669"
    "500" = "1d842c602f728fa1fa8e0a2ee5c2d2710a4c21583b826e01db7d512fd855b0ff"
}

$legacyV17AutoSupplyV1Hashes = @{
    "1" = "32ae37be641f5c0f025bc35ecddf008f0b2199de8ba52fdd2b9f84cc1c4214b6"
    "2" = "fc677753a35ada8be0811e48d622b18a5952de4f0aa67cac876d06aab20e6459"
    "5" = "bba527cb7bdac8df0b02b30af0cae0c064a2b69390d5cfd3b72eab874a025d00"
    "10" = "cfc80ce7d8158dfdce217b6cb69423559f86735c2c0add0c5a0e730eecfd353d"
    "20" = "723d9fe46ab6700501281d32863fc36b0f12a920419f3597da4f16876ea9a8a0"
    "50" = "61c23795d9e53f9e51c2b68cdc3152c621938b91ca4f1d30be00394d55ba715f"
    "500" = "99d8afdc70dbc5b7e8692ffb296d069a6ba3572c5f8948ac76d1a22d7b1bff21"
}

$legacyV17EveryFrameHashes = @{
    "1" = "3338b9e8457156d869cfbfb82998b08e37d9f192c10b3b166770f9372e91af4c"
    "2" = "3cf4a1355d6b1db4ad2112cb79328692dbd9b370fc51454d1f77365badd7c91c"
    "5" = "52dbf0e1ebf010cb9ff1ec7a04e4cf6eea7f55d229b1b8df16150379d75d82a7"
    "10" = "746e1fb4c0ce92bbd1e61e8347415c0cd4965b1a69cc3c4e0ee41e3d8fb6baf6"
    "20" = "a1822fea9c384655de53a957b8d8aff702be64bc8f382f9cb2f34ec00cc1f962"
    "50" = "4ea6d68c7a69dbe9218a5f2dc06c77cdc0c8e593ed541d38c92846922766826b"
    "500" = "55c2904d9cf97281c428af5e0f36dd8fa3787e2d4f79283b5748ce13e273511c"
}

$legacyV17Hashes = @{
    "1" = "1d47232d1f9d31fe91f127316cefa888d976d9100e04886e1bab257bc2e93c7d"
    "2" = "c41d61989e1bb3d2f2e8e7582cd8adc3181c26e2375c78efa4e523d6a4f8ae8b"
    "5" = "6085f4fa43687758feb30a6be5eea5ff9dccf9b613a559af7f16c12eb822d04c"
    "10" = "c46f0b0bc8ee810badb351657cc514b3da7cd5a37b9e787986e8603ec4b25dd9"
    "20" = "9e0270b96bd1f22ec5acf8d02c8ac70e1af086a5373ed970c5985f678d2b97c4"
    "50" = "cbce1e4ea53e8b7b41ead71b87a08a7c299fe7e2f6f0e019037ff4f8dcc303b0"
}

$legacyV17Fast2Hashes = @{
    "1" = "33f412d7fe9d5e87f717c7f664b4824f8c9f08a5b1d852d672a7619800ecad7f"
    "2" = "0fd5a15099edc859f94aee5ed4e0eb8c4dcb2a930a7b2725061c3f0597a9c2d5"
    "5" = "3c798803e2daa63450085f9a96f99d647e0e07c36c62ae3448b66f049639564f"
    "10" = "9ebf1d260f3c6444963a2af855a7830ce993bb8cba048282fa5d37b6152334d8"
    "20" = "206d4661a30b756f1cc4c8f5510afa55032b7d3522bd00e88315d943dec56332"
    "50" = "ec50300f5f1eff5c97bf7819a41099814f3ea8c61eb6420a4a48b0f7d9415808"
}

$legacyV17Fast4Hashes = @{
    "1" = "205747ca878c7bc0a556bb5f60a95bd12a0e0573cacc0dab677b36f2bae45d84"
    "2" = "3cf164a47412ab6469fd760ba20a0e36c928b06927885f1c9b63d3b5fc0b3fbb"
    "5" = "8d874640e02f50b67a9a8a303d3754b76577955651b6a0ac39f4c8c2d266d87a"
    "10" = "a77aa04df07e0a1db950d07a93edebff75af99221a69481e55648074be0eedc6"
    "20" = "0eb54ffc829a5ba2ed904364427e0dab523ad345ef450b3adf43da045f857e11"
    "50" = "281d7846a28544af1153319d805e21c7f619bfe2addfacad3a87b559e147dd32"
}

$legacyV16Hashes = @{
    "1" = "fe4f3d8b26a5256fa000b5b7fe01600d7f661688b404edfdf50f11c861ffdf42"
    "2" = "9da1f8cf8aea029c529ebf6879dd9cd0b9772ea8b5c128d702281a5d070d3718"
    "5" = "71e9846570e0a6eed71062ac35bed2eb484ff816999f884c036e2109741af17d"
    "10" = "aa0c305e9b377a67449af4ec806f650db8ad271b13b26409aef92b4811d54aba"
    "20" = "aa58adc25848b96fc2fee95d9c8d69ad2e25c289abcb76f0978dfa0940ccbb97"
    "50" = "81b25919cafac31083a987b8be0a2d770fa8201412ea5bba55717153260f69ed"
}

$legacyV15Hashes = @{
    "1" = "28ff81a0a537f30727a99356e0a41068ef3dcac8c9f4b887a7d5c381dc72a317"
    "2" = "ef12d5dd40a7b26b5ff6ff0d60ddeda1437486dea69d2093b0016f777b6dba76"
    "5" = "f4b7a1f8121d99884b22e502b254f1c6630b0014d4bfa3696ad2b22319679522"
    "10" = "c7521735da2563012504bd64862afdd5944672fa6fad0db7ddb8400156f50792"
    "20" = "a24225a09eb4ca117ef846a76ca057ca8b863e01758236ea36c1b4319ac6626a"
    "50" = "27ce1ed2703c70acc2a6950333c57016f22b57cac24e6d30c2a657ea770ab99d"
}

$legacyV14Hashes = @{
    "1" = "2a127d0592918c9b9db8400fc901275f49d9ff47c31d6afdd3c4071bae5eab84"
    "2" = "08f9999091b1a0d4931ba7a9312a76195d3b3f70c64db528e4840a7a0154abf5"
    "5" = "6a4d73889d197fddb87fbf83e000720523dffb85c4e093e75370a6be3416482d"
    "10" = "489e5d694045de50bcb0a2e41bb83a9eb2b49fc3111ae71ee74c2413098e4c65"
    "20" = "baf232c6fe6c475ff8f6eed957bd50ae0634d0632f288e6ee535279902133e4b"
    "50" = "71a6476dd2775bd33d8fcae2b3761e345d0418cd7be4a7bb33c7e4f755f90793"
}

$legacyV13Hashes = @{
    "1" = "89088f13c8d93bb1bcbcf045f6a6bdd6a938dbbca81fcfc14ef001017fb91aad"
    "2" = "77c83a609c4cfba5cb4aa0dfc01edfb398168df3dbd1186e6b28b17aacd25091"
    "5" = "3390ee732212fe276e1a67ec74986045d84e92cf4f3ccf9256bfb18b69e34485"
    "10" = "7130eabada714630cf84b5bcdaf4807dba1bfab559ed1d8cc846135ab1e7899e"
    "20" = "c85f3d261ea7eaf169a673e094ad4c9d4418b3a94907c90d8796f530a004059b"
    "50" = "9758d5cc557ddbd5c7bb72e469c3df9edc41b40ff868f06f3974ab25c9c2e42c"
}

$legacyV12Hashes = @{
    "1" = "04ba0250022917b4c20e345c4c50cc8bb0fb73dbf0ac97b893dffc55c5bf9230"
    "2" = "910cd27bfd55a28189b3c42c9336d9a9129a986d6d0115c55c33ad63be2eb091"
    "5" = "b85568c9d279678c3613e805c72e5cdc46c4d2bda267a67b0767321b3e69547b"
    "10" = "65f6c7b88eeb301138524f43ec22080502fd0313c86360497cfb440205cb338d"
    "20" = "30b64a1f774c741a524c57574d028aeef9baf454d3ad4cdb6948c4acfd576fe6"
    "50" = "45cd700ef648de5fadfecf513a579e29df3a92dda4178f6784ddc3d483a04049"
}

function Show-Result([string]$Text, [string]$Title, [string]$Kind = "Info") {
    Write-Host ""
    Write-Host $Text -ForegroundColor $(if ($Kind -eq "Error") { "Red" } elseif ($Kind -eq "Success") { "Green" } else { "Cyan" })
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $icon = if ($Kind -eq "Error") { [System.Windows.Forms.MessageBoxIcon]::Error } elseif ($Kind -eq "Success") { [System.Windows.Forms.MessageBoxIcon]::Information } else { [System.Windows.Forms.MessageBoxIcon]::Information }
        [void][System.Windows.Forms.MessageBox]::Show($Text, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, $icon)
    } catch { }
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Add-Candidate([System.Collections.Generic.List[string]]$List, [string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    try { $full = [System.IO.Path]::GetFullPath($Path) } catch { return }
    if (-not $List.Contains($full)) { $List.Add($full) }
}

function Find-GameRoot {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    $savedPathFile = Join-Path $packageRoot "last_game_path.txt"
    if (Test-Path -LiteralPath $savedPathFile) {
        Add-Candidate $candidates ((Get-Content -LiteralPath $savedPathFile -Raw).Trim())
    }
    Add-Candidate $candidates (Get-Location).Path
    Add-Candidate $candidates $packageRoot
    Add-Candidate $candidates (Split-Path -Parent $packageRoot)

    $steamRoots = New-Object 'System.Collections.Generic.List[string]'
    try {
        $reg = Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction Stop
        Add-Candidate $steamRoots $reg.SteamPath
    } catch { }
    try {
        $reg = Get-ItemProperty -Path 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam' -ErrorAction Stop
        Add-Candidate $steamRoots $reg.InstallPath
    } catch { }
    if (${env:ProgramFiles(x86)}) { Add-Candidate $steamRoots (Join-Path ${env:ProgramFiles(x86)} 'Steam') }
    if ($env:ProgramFiles) { Add-Candidate $steamRoots (Join-Path $env:ProgramFiles 'Steam') }

    foreach ($steamRoot in @($steamRoots)) {
        Add-Candidate $candidates (Join-Path $steamRoot 'steamapps\common\Meow My Crop!')
        $vdf = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($line in Get-Content -LiteralPath $vdf -ErrorAction SilentlyContinue) {
                if ($line -match '"path"\s+"([^"]+)"') {
                    $library = $matches[1] -replace '\\\\','\'
                    Add-Candidate $candidates (Join-Path $library 'steamapps\common\Meow My Crop!')
                }
            }
        }
    }
    foreach ($drive in [System.IO.DriveInfo]::GetDrives()) {
        if (-not $drive.IsReady) { continue }
        Add-Candidate $candidates (Join-Path $drive.RootDirectory.FullName 'SteamLibrary\steamapps\common\Meow My Crop!')
        Add-Candidate $candidates (Join-Path $drive.RootDirectory.FullName 'Steam\steamapps\common\Meow My Crop!')
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate $relativeTarget)) { return $candidate }
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = 'Select the Meow My Crop! game folder (the folder containing MeowMyCrop.exe).'
        $dialog.ShowNewFolderButton = $false
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            if (Test-Path -LiteralPath (Join-Path $dialog.SelectedPath $relativeTarget)) { return $dialog.SelectedPath }
            throw "The selected folder does not contain $relativeTarget"
        }
    } catch {
        Write-Host "Folder selection failed or was cancelled: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    $typed = Read-Host 'Paste the full game folder path, or press Enter to cancel'
    if (-not [string]::IsNullOrWhiteSpace($typed)) {
        $typed = $typed.Trim('"')
        if (Test-Path -LiteralPath (Join-Path $typed $relativeTarget)) { return [System.IO.Path]::GetFullPath($typed) }
    }
    return $null
}

function Get-Game-Processes([string]$Root) {
    $expectedExe = [System.IO.Path]::GetFullPath((Join-Path $Root 'MeowMyCrop.exe'))
    $found = @()
    foreach ($proc in @(Get-Process -Name 'MeowMyCrop' -ErrorAction SilentlyContinue)) {
        $matchesThisGame = $false
        try {
            if ($proc.Path) {
                $matchesThisGame = ([System.IO.Path]::GetFullPath($proc.Path) -ieq $expectedExe)
            } else {
                # Older PowerShell/permissions may hide Path. The exact process name is still a strong match.
                $matchesThisGame = $true
            }
        } catch {
            $matchesThisGame = $true
        }
        if ($matchesThisGame) { $found += $proc }
    }
    return @($found)
}

function Ensure-Game-Closed([string]$Root) {
    while ($true) {
        $running = @(Get-Game-Processes $Root)
        if ($running.Count -eq 0) { return }

        $details = ($running | ForEach-Object {
            $pathText = ''
            try { $pathText = $_.Path } catch { }
            if ([string]::IsNullOrWhiteSpace($pathText)) { $pathText = '(path unavailable)' }
            "PID $($_.Id)  $pathText"
        }) -join "`n"

        Write-Host ''
        Write-Host 'The game process is still running:' -ForegroundColor Yellow
        Write-Host $details -ForegroundColor Yellow
        Write-Host 'The DLL cannot be replaced safely while this process is open.' -ForegroundColor Yellow

        $choice = $null
        try {
            Add-Type -AssemblyName System.Windows.Forms
            $message = "Meow My Crop is still running in the background:`n`n$details`n`nYes = close it automatically`nNo = check again after you close it yourself`nCancel = stop installation"
            $choice = [System.Windows.Forms.MessageBox]::Show(
                $message,
                'Meow My Crop MOD - Game Still Running',
                [System.Windows.Forms.MessageBoxButtons]::YesNoCancel,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
        } catch { }

        if ($choice -eq [System.Windows.Forms.DialogResult]::Yes) {
            foreach ($proc in $running) {
                try {
                    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                    Write-Host "Closed process PID $($proc.Id)." -ForegroundColor Green
                } catch {
                    throw "Could not close MeowMyCrop.exe (PID $($proc.Id)). Close it in Task Manager, then retry. $($_.Exception.Message)"
                }
            }
            Start-Sleep -Milliseconds 800
            continue
        }
        elseif ($choice -eq [System.Windows.Forms.DialogResult]::No) {
            Start-Sleep -Milliseconds 500
            continue
        }
        elseif ($choice -eq [System.Windows.Forms.DialogResult]::Cancel) {
            throw 'Installation cancelled because the game is still running.'
        }

        # Console fallback if Windows Forms is unavailable.
        $answer = (Read-Host 'Enter K to close the process automatically, R to recheck, or C to cancel').Trim().ToUpperInvariant()
        if ($answer -eq 'K') {
            foreach ($proc in $running) { Stop-Process -Id $proc.Id -Force -ErrorAction Stop }
            Start-Sleep -Milliseconds 800
        } elseif ($answer -eq 'C') {
            throw 'Installation cancelled because the game is still running.'
        }
    }
}

function Select-Speed([int]$DefaultSpeed = 10) {
    Write-Host ''
    Write-Host 'Choose growth speed:' -ForegroundColor Cyan
    Write-Host '  1 = 1x   (original growth per key event)'
    Write-Host '  2 = 2x'
    Write-Host '  3 = 5x'
    Write-Host '  4 = 10x  (recommended)'
    Write-Host '  5 = 20x'
    Write-Host '  6 = 50x  (very fast)'
    Write-Host '  7 = 500x (extreme)'
    $map = @{ '1'=1; '2'=2; '3'=5; '4'=10; '5'=20; '6'=50; '7'=500 }
    $choice = Read-Host "Enter 1-7, or press Enter to keep ${DefaultSpeed}x"
    if ([string]::IsNullOrWhiteSpace($choice)) { return $DefaultSpeed }
    if (-not $map.ContainsKey($choice)) { throw 'Invalid speed selection. Enter a number from 1 to 7.' }
    return [int]$map[$choice]
}

function Detect-Installed-Speed([string]$Hash) {
    foreach ($key in $variantHashes.Keys) {
        if ($variantHashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V17-Speed([string]$Hash) {
    foreach ($key in $legacyV17LatestHashes.Keys) {
        if ($legacyV17LatestHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17OriginalInstanceHashes.Keys) {
        if ($legacyV17OriginalInstanceHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoSupplyRefreshHashes.Keys) {
        if ($legacyV17AutoSupplyRefreshHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17StartupAutoOnHashes.Keys) {
        if ($legacyV17StartupAutoOnHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17VisibleActiveHashes.Keys) {
        if ($legacyV17VisibleActiveHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17VisibleFruitOnlyHashes.Keys) {
        if ($legacyV17VisibleFruitOnlyHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17FruitTokenGateHashes.Keys) {
        if ($legacyV17FruitTokenGateHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoCanEventLockHashes.Keys) {
        if ($legacyV17AutoCanEventLockHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoCanFilteredInstanceHashes.Keys) {
        if ($legacyV17AutoCanFilteredInstanceHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoCanSharedEntryGuardHashes.Keys) {
        if ($legacyV17AutoCanSharedEntryGuardHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoCanEntryGuardHashes.Keys) {
        if ($legacyV17AutoCanEntryGuardHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoCanRefreshAccessHashes.Keys) {
        if ($legacyV17AutoCanRefreshAccessHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoCanGuardHashes.Keys) {
        if ($legacyV17AutoCanGuardHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoSupplyReentryHashes.Keys) {
        if ($legacyV17AutoSupplyReentryHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoSupplyV1Hashes.Keys) {
        if ($legacyV17AutoSupplyV1Hashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17EveryFrameHashes.Keys) {
        if ($legacyV17EveryFrameHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17Hashes.Keys) {
        if ($legacyV17Hashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17Fast2Hashes.Keys) {
        if ($legacyV17Fast2Hashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17Fast4Hashes.Keys) {
        if ($legacyV17Fast4Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V16-Speed([string]$Hash) {
    foreach ($key in $legacyV16Hashes.Keys) {
        if ($legacyV16Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V15-Speed([string]$Hash) {
    foreach ($key in $legacyV15Hashes.Keys) {
        if ($legacyV15Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V14-Speed([string]$Hash) {
    foreach ($key in $legacyV14Hashes.Keys) {
        if ($legacyV14Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V13-Speed([string]$Hash) {
    foreach ($key in $legacyV13Hashes.Keys) {
        if ($legacyV13Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V12-Speed([string]$Hash) {
    foreach ($key in $legacyV12Hashes.Keys) {
        if ($legacyV12Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

$transcriptStarted = $false
try {
    Start-Transcript -Path $logPath -Append | Out-Null
    $transcriptStarted = $true
    Write-Host '=====================================================' -ForegroundColor Cyan
    Write-Host " Meow My Crop! MOD Manager v1.8 - $Mode" -ForegroundColor Cyan
    Write-Host '=====================================================' -ForegroundColor Cyan
    Write-Host "Package folder: $packageRoot"
    Write-Host "Log file: $logPath"

    $root = Find-GameRoot
    if (-not $root) { throw 'No valid game folder was selected.' }
    Ensure-Game-Closed $root
    Set-Content -LiteralPath (Join-Path $packageRoot 'last_game_path.txt') -Value $root -Encoding UTF8

    $target = Join-Path $root $relativeTarget
    $backup = "$target.meowmod_backup"
    $currentHash = Get-Hash $target
    $installedSpeed = Detect-Installed-Speed $currentHash
    $legacyV12Speed = Detect-Legacy-V12-Speed $currentHash
    $legacyV13Speed = Detect-Legacy-V13-Speed $currentHash
    $legacyV14Speed = Detect-Legacy-V14-Speed $currentHash
    $legacyV15Speed = Detect-Legacy-V15-Speed $currentHash
    $legacyV16Speed = Detect-Legacy-V16-Speed $currentHash
    $legacyV17Speed = Detect-Legacy-V17-Speed $currentHash
    $isLegacyV10 = ($currentHash -eq $legacyV10Hash)
    Write-Host "Game folder: $root"
    Write-Host "Current DLL SHA256: $currentHash"

    if ($Mode -eq 'Uninstall') {
        if ($currentHash -eq $originalHash) {
            Remove-Item -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -ErrorAction SilentlyContinue
            Show-Result 'The supported original Assembly-CSharp.dll is already installed. No game file was overwritten.' 'Meow My Crop MOD' 'Success'
            exit 0
        }
        $isKnownManagedMod = ($installedSpeed -gt 0) -or ($legacyV12Speed -gt 0) -or ($legacyV13Speed -gt 0) -or ($legacyV14Speed -gt 0) -or ($legacyV15Speed -gt 0) -or ($legacyV16Speed -gt 0) -or ($legacyV17Speed -gt 0) -or $isLegacyV10
        if (-not $isKnownManagedMod) { throw 'The current Assembly-CSharp.dll is not a known MeowMOD file. It may belong to a game update or another MOD, so it was not overwritten.' }
        if (-not (Test-Path -LiteralPath $backup)) { throw 'Backup file not found. Use Steam Verify Integrity to restore the original game file.' }
        $backupHash = Get-Hash $backup
        if ($backupHash -ne $originalHash) { throw 'The backup hash is not the expected original version. It was not restored for safety.' }
        Copy-Item -LiteralPath $backup -Destination $target -Force
        if ((Get-Hash $target) -ne $originalHash) { throw 'Uninstall copy verification failed.' }
        Remove-Item -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -ErrorAction SilentlyContinue
        Show-Result 'MOD uninstalled successfully. The original Assembly-CSharp.dll was restored.' 'Meow My Crop MOD' 'Success'
        exit 0
    }

    if (($currentHash -ne $originalHash) -and ($installedSpeed -eq 0) -and ($legacyV12Speed -eq 0) -and ($legacyV13Speed -eq 0) -and ($legacyV14Speed -eq 0) -and ($legacyV15Speed -eq 0) -and ($legacyV16Speed -eq 0) -and ($legacyV17Speed -eq 0) -and (-not $isLegacyV10)) {
        throw 'This Assembly-CSharp.dll is neither the supported original file nor a known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7/v1.8 MOD file. The game may have updated or another MOD may already modify it.'
    }
    if ($installedSpeed -gt 0) {
        if (-not (Test-Path -LiteralPath $backup)) { throw 'MeowMOD v1.8 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'MeowMOD v1.8 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($isLegacyV10) {
        Write-Host 'Detected v1.0 MOD. It can be upgraded directly to v1.8.' -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.0 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.0 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV17Speed -gt 0) {
        Write-Host "Detected v1.7 (${legacyV17Speed}x). Updating to v1.8 with independent 100-count limits and saved F8 state." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'An earlier v1.7 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'Earlier v1.7 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV16Speed -gt 0) {
        Write-Host "Detected v1.6 (${legacyV16Speed}x). v1.8 adds independent 100-count limits, exact counter logs, and full recipe shortage scanning." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.6 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.6 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV15Speed -gt 0) {
        Write-Host "Detected v1.5 (${legacyV15Speed}x). v1.8 includes automatic can opening and local Legendary/orange decoration rarity." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.5 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.5 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV14Speed -gt 0) {
        Write-Host "Detected v1.4 (${legacyV14Speed}x). v1.8 preserves automatic steal/lost events without the one-fruit skip." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.4 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.4 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV13Speed -gt 0) {
        Write-Host "Detected v1.3 (${legacyV13Speed}x). v1.8 will preserve automatic offline steal and automatic being-stolen events." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.3 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.3 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV12Speed -gt 0) {
        Write-Host "Detected v1.2 (${legacyV12Speed}x). v1.8 will repair input handling and guarantee automatic offline steal/loss events." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.2 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.8.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.2 backup hash is unexpected. It was not overwritten for safety.' }
    }

    $defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV17Speed -gt 0) { $legacyV17Speed } elseif ($legacyV16Speed -gt 0) { $legacyV16Speed } elseif ($legacyV15Speed -gt 0) { $legacyV15Speed } elseif ($legacyV14Speed -gt 0) { $legacyV14Speed } elseif ($legacyV13Speed -gt 0) { $legacyV13Speed } elseif ($legacyV12Speed -gt 0) { $legacyV12Speed } else { 10 }
    $speed = Select-Speed $defaultSpeed
    $modDll = Join-Path $packageRoot ("ModFiles\Assembly-CSharp_{0}x.dll" -f $speed)
    if (-not (Test-Path -LiteralPath $modDll)) { throw "Missing MOD variant: $modDll" }
    if ((Get-Hash $modDll) -ne $variantHashes[[string]$speed]) { throw 'MOD package integrity check failed. Re-extract the ZIP.' }

    if ($currentHash -eq $originalHash) {
        if (-not (Test-Path -LiteralPath $backup)) {
            Copy-Item -LiteralPath $target -Destination $backup -Force
            if ((Get-Hash $backup) -ne $originalHash) { throw 'Original backup verification failed. The MOD was not installed.' }
            Write-Host "Original backup created and verified: $backup" -ForegroundColor Yellow
        } elseif ((Get-Hash $backup) -ne $originalHash) {
            throw 'An existing backup file has an unexpected hash. Rename or remove it only after keeping a safe copy.'
        }
    }

    Copy-Item -LiteralPath $modDll -Destination $target -Force
    if ((Get-Hash $target) -ne $variantHashes[[string]$speed]) { throw 'Installation copy verification failed.' }
    @(
        'Meow My Crop! MeowMOD v1.8',
        "GrowthSpeed=${speed}x",
        'F5=Toggle automatic steal + automatic being-stolen (persistent)',
        'F6=Toggle internal automatic key delivery (persistent; physical input remains active)',
        'F7=Toggle automatic harvest + replant (persistent)',
        'F8=Toggle automatic can opening + missing-fruit crop supply (persistent)',
        'All four switches default to enabled on first run',
        'AutomaticStealLimit=100 (saved independently)',
        'AutomaticBeingStolenLimit=100 (saved independently)',
        'CounterLogs=[AutoSteal] n/100 and [AutoBeingStolen] n/100',
        'AutoCanRecipeScan=All required fruit entries',
        'GrowthMultiplier=Saved in MOD PlayerPrefs config',
        'DecorationRarityOverride=Local Legendary/orange display and classification',
        'No mouse movement or mouse capture is used',
        "Installed=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    ) | Set-Content -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -Encoding UTF8

    $verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MeowMOD v1.8 installed' }
    Show-Result "$verb successfully.`nGrowth speed: ${speed}x`n`nF5 = automatic steal + being-stolen (each stops at saved 100)`nF6 = internal automatic key delivery`nF7 = automatic harvest + replant`nF8 = automatic can opening + full missing-fruit scan`n`nF5 logs: [AutoSteal] n/100 and [AutoBeingStolen] n/100.`nManual online stealing, keyboard/mouse input, and the manual can button remain usable." 'Meow My Crop MOD' 'Success'
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Host ''
    Write-Host "FAILED: $message" -ForegroundColor Red
    Write-Host "Detailed log: $logPath" -ForegroundColor Yellow
    Show-Result "Operation failed:`n$message`n`nDetailed log:`n$logPath" 'Meow My Crop MOD - Error' 'Error'
    exit 1
}
finally {
    if ($transcriptStarted) { try { Stop-Transcript | Out-Null } catch { } }
}
