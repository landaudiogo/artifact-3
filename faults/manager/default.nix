{ pkgs }:
{
    devShell = pkgs.mkShell {
        packages = with pkgs; [ 
            python3 
            uv 
        ];
    };
}
