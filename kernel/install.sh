#!/bin/bash

h_name=$(ls -alrth | tail -1 | awk '{ print $9 }' | grep headers)
i_name=$(ls -alrth | tail -1 | awk '{ print $9 }' | grep image-5.17.4-smdk+_)

i=1
while [ -z $h_name ]; do
	i=$(( ${i}+1 ))
	h_name=$(ls -alrth | tail -$i | awk '{ print $9 }' | grep headers)
done
i=1
while [ -z $i_name ]; do
	i=$(( ${i}+1 ))
	i_name=$(ls -alrth | tail -$i | awk '{ print $9 }' | grep image-5.17.4-smdk+_)
done

echo "header: $h_name"
echo "image: $i_name"

cmd="dpkg -i $h_name $i_name"
echo "\$ $cmd"

echo "This command is right?"

read -r -p "Are you sure? [y/N] " response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
then
    echo "install.."
else
    exit
fi

$cmd

echo "kernel install end."
