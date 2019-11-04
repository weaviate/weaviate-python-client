
echo "Go to documentation branch"
git checkout documentation
echo "Get current code"
git merge master
echo "Build documentation $(pwd)"
make -C documentation html

echo "See if something is to commint"
git diff --exit-code
if [ $? -eq 0 ]; then
    echo "Documentation has not changed"
    exit 0
fi

echo "Documentation has changed build new one"
git add documentation
git commit -m "Autogenerating documentation 🤖"
git push origin documentation